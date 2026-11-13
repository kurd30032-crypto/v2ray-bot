from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
import logging

from keyboards.keyboards import (
    get_admin_configs_keyboard,
    get_config_edit_keyboard,
    get_back_keyboard,
    get_cancel_keyboard
)
from database.database import AsyncSessionLocal
from models.models import Config
from config import config

router = Router()
logger = logging.getLogger(__name__)

class ConfigStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_address = State()
    waiting_for_edit_name = State()
    waiting_for_edit_address = State()

# Admin filter
def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS

@router.callback_query(F.data == "admin_configs")
async def admin_configs(callback: CallbackQuery):
    """Show admin configs management"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Config).order_by(Config.created_at.desc())
            )
            configs = result.scalars().all()
            
            await callback.message.edit_text(
                "🔧 مدیریت کانفیگ‌ها:\n\n"
                "کانفیگ‌های موجود را مشاهده و مدیریت کنید.",
                reply_markup=get_admin_configs_keyboard(configs)
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in admin_configs: {e}")
        await callback.message.edit_text(
            "❌ خطا در دریافت کانفیگ‌ها.",
            reply_markup=get_back_keyboard("admin_panel")
        )
        await callback.answer()

@router.callback_query(F.data == "admin_add_config")
async def admin_add_config(callback: CallbackQuery, state: FSMContext):
    """Start add config process"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    await callback.message.edit_text(
        "➕ افزودن کانفیگ جدید:\n\n"
        "📛 لطفاً نام کانفیگ را وارد کنید:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(ConfigStates.waiting_for_name)
    await callback.answer()

@router.message(ConfigStates.waiting_for_name, F.text)
async def handle_config_name(message: Message, state: FSMContext):
    """Handle config name"""
    await state.update_data(name=message.text)
    
    await message.answer(
        "🔗 لطفاً آدرس کانفیگ V2Ray را وارد کنید:\n\n"
        "مثال: vmess://... یا vless://...",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(ConfigStates.waiting_for_address)

@router.message(ConfigStates.waiting_for_address, F.text)
async def handle_config_address(message: Message, state: FSMContext):
    """Handle config address"""
    await state.update_data(address=message.text)
    
    data = await state.get_data()
    
    try:
        async with AsyncSessionLocal() as session:
            config_obj = Config(
                name=data['name'],
                address=data['address']
            )
            session.add(config_obj)
            await session.commit()
            
            await message.answer(
                f"✅ کانفیگ '{config_obj.name}' با موفقیت ایجاد شد!",
                reply_markup=get_back_keyboard("admin_configs")
            )
            await state.clear()
            
    except Exception as e:
        logger.error(f"Error creating config: {e}")
        await message.answer(
            "❌ خطا در ایجاد کانفیگ.",
            reply_markup=get_back_keyboard("admin_configs")
        )
        await state.clear()

@router.callback_query(F.data.startswith("admin_config_"))
async def admin_config_detail(callback: CallbackQuery):
    """Show config detail"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    config_id = int(callback.data.split("_")[2])
    
    try:
        async with AsyncSessionLocal() as session:
            config_obj = await session.get(Config, config_id)
            
            if not config_obj:
                await callback.answer("❌ کانفیگ یافت نشد.")
                return
            
            status_emoji = "🟢" if config_obj.is_active else "🔴"
            
            text = f"🔧 جزئیات کانفیگ:\n\n"
            text += f"📛 نام: {config_obj.name}\n"
            text += f"🔗 آدرس: {config_obj.address[:100]}...\n"
            text += f"📊 وضعیت: {status_emoji}\n"
            text += f"📅 تاریخ ایجاد: {config_obj.created_at.strftime('%Y-%m-%d %H:%M')}"
            
            await callback.message.edit_text(
                text,
                reply_markup=get_config_edit_keyboard(config_id)
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in admin_config_detail: {e}")
        await callback.answer("❌ خطا در دریافت جزئیات کانفیگ.")

@router.callback_query(F.data.startswith("edit_config_"))
async def edit_config_start(callback: CallbackQuery, state: FSMContext):
    """Start config edit process"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    config_id = int(callback.data.split("_")[2])
    await state.update_data(edit_config_id=config_id)
    
    await callback.message.edit_text(
        "✏️ ویرایش کانفیگ:\n\n"
        "لطفاً نام جدید را وارد کنید (برای حفظ مقدار فعلی، 'همان' را وارد کنید):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(ConfigStates.waiting_for_edit_name)
    await callback.answer()

@router.message(ConfigStates.waiting_for_edit_name, F.text)
async def handle_edit_config_name(message: Message, state: FSMContext):
    """Handle edit config name"""
    await state.update_data(edit_name=message.text if message.text != "همان" else None)
    
    await message.answer(
        "🔗 آدرس جدید را وارد کنید (برای حفظ مقدار فعلی، 'همان' را وارد کنید):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(ConfigStates.waiting_for_edit_address)

@router.message(ConfigStates.waiting_for_edit_address, F.text)
async def handle_edit_config_address(message: Message, state: FSMContext):
    """Handle edit config address"""
    await state.update_data(edit_address=message.text if message.text != "همان" else None)
    
    data = await state.get_data()
    config_id = data.get('edit_config_id')
    
    try:
        async with AsyncSessionLocal() as session:
            config_obj = await session.get(Config, config_id)
            
            if not config_obj:
                await message.answer(
                    "❌ کانفیگ یافت نشد.",
                    reply_markup=get_back_keyboard("admin_configs")
                )
                await state.clear()
                return
            
            if data.get('edit_name') is not None:
                config_obj.name = data['edit_name']
            if data.get('edit_address') is not None:
                config_obj.address = data['edit_address']
            
            await session.commit()
            
            await message.answer(
                f"✅ کانفیگ '{config_obj.name}' با موفقیت ویرایش شد!",
                reply_markup=get_back_keyboard("admin_configs")
            )
            await state.clear()
            
    except Exception as e:
        logger.error(f"Error editing config: {e}")
        await message.answer(
            "❌ خطا در ویرایش کانفیگ.",
            reply_markup=get_back_keyboard("admin_configs")
        )
        await state.clear()

@router.callback_query(F.data.startswith("delete_config_"))
async def delete_config(callback: CallbackQuery):
    """Delete config"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    config_id = int(callback.data.split("_")[2])
    
    try:
        async with AsyncSessionLocal() as session:
            config_obj = await session.get(Config, config_id)
            
            if not config_obj:
                await callback.answer("❌ کانفیگ یافت نشد.")
                return
            
            await session.delete(config_obj)
            await session.commit()
            
            await callback.message.edit_text(
                f"✅ کانفیگ '{config_obj.name}' با موفقیت حذف شد.",
                reply_markup=get_back_keyboard("admin_configs")
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error deleting config: {e}")
        await callback.message.edit_text(
            "❌ خطا در حذف کانفیگ.",
            reply_markup=get_back_keyboard("admin_configs")
        )
        await callback.answer()

@router.callback_query(F.data.startswith("toggle_config_"))
async def toggle_config(callback: CallbackQuery):
    """Toggle config active status"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    config_id = int(callback.data.split("_")[2])
    
    try:
        async with AsyncSessionLocal() as session:
            config_obj = await session.get(Config, config_id)
            
            if not config_obj:
                await callback.answer("❌ کانفیگ یافت نشد.")
                return
            
            config_obj.is_active = not config_obj.is_active
            await session.commit()
            
            status = "فعال" if config_obj.is_active else "غیرفعال"
            await callback.message.edit_text(
                f"✅ وضعیت کانفیگ '{config_obj.name}' به '{status}' تغییر یافت.",
                reply_markup=get_back_keyboard("admin_configs")
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error toggling config: {e}")
        await callback.message.edit_text(
            "❌ خطا در تغییر وضعیت کانفیگ.",
            reply_markup=get_back_keyboard("admin_configs")
        )
        await callback.answer()