from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
import logging

from keyboards.keyboards import (
    get_settings_keyboard,
    get_back_keyboard,
    get_cancel_keyboard,
    get_required_channels_keyboard,
    get_channel_edit_keyboard,
    get_confirmation_keyboard 
)
from database.database import AsyncSessionLocal
from models.models import Setting, SalesChannel, RequiredChannel
from config import config

router = Router()
logger = logging.getLogger(__name__)

class SettingsStates(StatesGroup):
    waiting_for_welcome_text = State()
    waiting_for_rules_text = State()
    waiting_for_guide_text = State()
    waiting_for_admin_ids = State()
    waiting_for_channel_id = State()
    waiting_for_edit_channel_id = State()
    waiting_for_required_channel_id = State()
    waiting_for_edit_required_channel_id = State()

# Admin filter
def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS

@router.callback_query(F.data == "admin_settings")
async def admin_settings(callback: CallbackQuery):
    """Show settings menu"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    await callback.message.edit_text(
        "⚙️ تنظیمات:\n\n"
        "از منوی زیر برای مدیریت تنظیمات ربات استفاده کنید.",
        reply_markup=get_settings_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "admin_edit_welcome")
async def edit_welcome_text(callback: CallbackQuery, state: FSMContext):
    """Start edit welcome text"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Setting).where(Setting.key == 'welcome_text')
        )
        welcome = result.scalar_one_or_none()
        current_text = welcome.value if welcome else config.DEFAULT_WELCOME_TEXT
    
    await callback.message.edit_text(
        f"✏️ ویرایش متن خوش‌آمدگویی:\n\n"
        f"متن فعلی:\n{current_text}\n\n"
        f"لطفاً متن جدید را وارد کنید:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(SettingsStates.waiting_for_welcome_text)
    await callback.answer()

@router.message(SettingsStates.waiting_for_welcome_text, F.text)
async def handle_welcome_text(message: Message, state: FSMContext):
    """Handle welcome text update"""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Setting).where(Setting.key == 'welcome_text')
            )
            setting = result.scalar_one_or_none()
            
            if setting:
                setting.value = message.text
            else:
                setting = Setting(key='welcome_text', value=message.text)
                session.add(setting)
            
            await session.commit()
            
            await message.answer(
                "✅ متن خوش‌آمدگویی با موفقیت به‌روزرسانی شد.",
                reply_markup=get_back_keyboard("admin_settings")
            )
            await state.clear()
            
    except Exception as e:
        logger.error(f"Error updating welcome text: {e}")
        await message.answer(
            "❌ خطا در به‌روزرسانی متن خوش‌آمدگویی.",
            reply_markup=get_back_keyboard("admin_settings")
        )
        await state.clear()

@router.callback_query(F.data == "admin_edit_rules")
async def edit_rules_text(callback: CallbackQuery, state: FSMContext):
    """Start edit rules text"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Setting).where(Setting.key == 'rules_text')
        )
        rules = result.scalar_one_or_none()
        current_text = rules.value if rules else config.DEFAULT_RULES_TEXT
    
    await callback.message.edit_text(
        f"✏️ ویرایش قوانین:\n\n"
        f"متن فعلی:\n{current_text}\n\n"
        f"لطفاً متن جدید را وارد کنید:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(SettingsStates.waiting_for_rules_text)
    await callback.answer()

@router.message(SettingsStates.waiting_for_rules_text, F.text)
async def handle_rules_text(message: Message, state: FSMContext):
    """Handle rules text update"""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Setting).where(Setting.key == 'rules_text')
            )
            setting = result.scalar_one_or_none()
            
            if setting:
                setting.value = message.text
            else:
                setting = Setting(key='rules_text', value=message.text)
                session.add(setting)
            
            await session.commit()
            
            await message.answer(
                "✅ قوانین با موفقیت به‌روزرسانی شد.",
                reply_markup=get_back_keyboard("admin_settings")
            )
            await state.clear()
            
    except Exception as e:
        logger.error(f"Error updating rules text: {e}")
        await message.answer(
            "❌ خطا در به‌روزرسانی قوانین.",
            reply_markup=get_back_keyboard("admin_settings")
        )
        await state.clear()

@router.callback_query(F.data == "admin_edit_guide")
async def edit_guide_text(callback: CallbackQuery, state: FSMContext):
    """Start edit guide text"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Setting).where(Setting.key == 'guide_text')
        )
        guide = result.scalar_one_or_none()
        current_text = guide.value if guide else config.DEFAULT_GUIDE_TEXT
    
    await callback.message.edit_text(
        f"✏️ ویرایش راهنمای اتصال:\n\n"
        f"متن فعلی:\n{current_text}\n\n"
        f"لطفاً متن جدید را وارد کنید:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(SettingsStates.waiting_for_guide_text)
    await callback.answer()

@router.message(SettingsStates.waiting_for_guide_text, F.text)
async def handle_guide_text(message: Message, state: FSMContext):
    """Handle guide text update"""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Setting).where(Setting.key == 'guide_text')
            )
            setting = result.scalar_one_or_none()
            
            if setting:
                setting.value = message.text
            else:
                setting = Setting(key='guide_text', value=message.text)
                session.add(setting)
            
            await session.commit()
            
            await message.answer(
                "✅ راهنمای اتصال با موفقیت به‌روزرسانی شد.",
                reply_markup=get_back_keyboard("admin_settings")
            )
            await state.clear()
            
    except Exception as e:
        logger.error(f"Error updating guide text: {e}")
        await message.answer(
            "❌ خطا در به‌روزرسانی راهنمای اتصال.",
            reply_markup=get_back_keyboard("admin_settings")
        )
        await state.clear()

@router.callback_query(F.data == "admin_edit_admins")
async def edit_admins(callback: CallbackQuery, state: FSMContext):
    """Start edit admins"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    current_admins = ", ".join([str(id) for id in config.ADMIN_IDS])
    
    await callback.message.edit_text(
        f"👤 مدیریت مدیران:\n\n"
        f"شناسه‌های مدیران فعلی:\n{current_admins}\n\n"
        f"📝 برای افزودن مدیر جدید، شناسه تلگرام او را وارد کنید.\n"
        f"⚠️ توجه: شناسه‌ها با کاما جدا شوند.",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(SettingsStates.waiting_for_admin_ids)
    await callback.answer()

@router.message(SettingsStates.waiting_for_admin_ids, F.text)
async def handle_admin_ids(message: Message, state: FSMContext):
    """Handle admin IDs update"""
    try:
        admin_ids = [int(id.strip()) for id in message.text.split(',') if id.strip().isdigit()]
        
        if not admin_ids:
            await message.answer(
                "❌ شناسه معتبری وارد نشد. لطفاً دوباره تلاش کنید:",
                reply_markup=get_cancel_keyboard()
            )
            return
        
        # Update config
        config.ADMIN_IDS = admin_ids
        
        # Save to database
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Setting).where(Setting.key == 'admin_ids')
            )
            setting = result.scalar_one_or_none()
            
            if setting:
                setting.value = message.text
            else:
                setting = Setting(key='admin_ids', value=message.text)
                session.add(setting)
            
            await session.commit()
        
        await message.answer(
            f"✅ مدیران با موفقیت به‌روزرسانی شدند.\n\n"
            f"👤 مدیران جدید: {', '.join([str(id) for id in admin_ids])}",
            reply_markup=get_back_keyboard("admin_settings")
        )
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error updating admins: {e}")
        await message.answer(
            "❌ خطا در به‌روزرسانی مدیران.",
            reply_markup=get_back_keyboard("admin_settings")
        )
        await state.clear()

@router.callback_query(F.data == "admin_channel")
async def admin_channel(callback: CallbackQuery):
    """Show channel management"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    try:
        async with AsyncSessionLocal() as session:
            # Get sales channel
            result = await session.execute(
                select(SalesChannel).where(SalesChannel.is_active == True)
            )
            sales_channel = result.scalar_one_or_none()
            
            # Get required channels
            result = await session.execute(
                select(RequiredChannel).where(RequiredChannel.is_active == True)
            )
            required_channels = result.scalars().all()
            
            text = "📢 <b>مدیریت کانال‌ها</b>\n\n"
            text += "📤 <b>کانال فروش:</b>\n"
            if sales_channel:
                text += f"✅ شناسه: {sales_channel.channel_id}\n"
            else:
                text += "❌ هیچ کانالی ثبت نشده است.\n"
            
            text += "\n🔒 <b>کانال‌های اجباری:</b>\n"
            if required_channels:
                for ch in required_channels:
                    text += f"✅ {ch.channel_title or ch.channel_id}\n"
            else:
                text += "❌ هیچ کانال اجباری ثبت نشده است.\n"
            
            await callback.message.edit_text(
                text,
                reply_markup=get_back_keyboard("admin_panel"),
                parse_mode="HTML"
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in admin_channel: {e}")
        await callback.message.edit_text(
            "❌ خطا در دریافت اطلاعات کانال‌ها.",
            reply_markup=get_back_keyboard("admin_panel")
        )
        await callback.answer()

@router.callback_query(F.data == "admin_required_channels")
async def admin_required_channels(callback: CallbackQuery):
    """Show required channels management"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(RequiredChannel).order_by(RequiredChannel.created_at.desc())
            )
            channels = result.scalars().all()
            
            await callback.message.edit_text(
                "🔒 <b>مدیریت کانال‌های اجباری</b>\n\n"
                "کاربران برای استفاده از ربات باید در این کانال‌ها عضو باشند.\n\n"
                "کانال‌های فعلی:",
                reply_markup=get_required_channels_keyboard(channels),
                parse_mode="HTML"
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in admin_required_channels: {e}")
        await callback.message.edit_text(
            "❌ خطا در دریافت کانال‌های اجباری.",
            reply_markup=get_back_keyboard("admin_settings")
        )
        await callback.answer()

@router.callback_query(F.data == "admin_add_required_channel")
async def admin_add_required_channel(callback: CallbackQuery, state: FSMContext):
    """Start add required channel process"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    await callback.message.edit_text(
        "➕ <b>افزودن کانال اجباری</b>\n\n"
        "لطفاً شناسه کانال را وارد کنید.\n"
        "⚠️ توجه: ربات باید در کانال عضو باشد و دسترسی ارسال پیام داشته باشد.\n\n"
        "مثال: @my_channel یا -100123456789",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(SettingsStates.waiting_for_required_channel_id)
    await callback.answer()

@router.message(SettingsStates.waiting_for_required_channel_id, F.text)
async def handle_required_channel_id(message: Message, state: FSMContext):
    """Handle required channel ID"""
    channel_input = message.text.strip()
    
    try:
        # Try to get channel info
        channel_info = None
        channel_id = channel_input
        channel_username = None
        channel_title = None
        
        # If it's a username, try to get channel info
        if channel_input.startswith('@'):
            channel_username = channel_input
            try:
                chat = await message.bot.get_chat(channel_input)
                channel_id = str(chat.id)
                channel_title = chat.title
            except Exception as e:
                logger.error(f"Error getting channel info: {e}")
                await message.answer(
                    "⚠️ خطا در دریافت اطلاعات کانال.\n"
                    "اطمینان حاصل کنید که ربات در کانال عضو است و شناسه کانال صحیح است.\n"
                    "آیا می‌خواهید با همین شناسه ادامه دهید؟",
                    reply_markup=get_confirmation_keyboard("force_channel", channel_input)
                )
                return
        
        async with AsyncSessionLocal() as session:
            # Check if channel already exists
            result = await session.execute(
                select(RequiredChannel).where(RequiredChannel.channel_id == channel_id)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                existing.is_active = True
                await session.commit()
                await message.answer(
                    f"✅ کانال با شناسه {channel_id} قبلاً ثبت شده بود و مجدداً فعال شد.",
                    reply_markup=get_back_keyboard("admin_required_channels")
                )
                await state.clear()
                return
            
            # Create new required channel
            channel = RequiredChannel(
                channel_id=channel_id,
                channel_username=channel_username,
                channel_title=channel_title
            )
            session.add(channel)
            await session.commit()
            
            await message.answer(
                f"✅ کانال اجباری با موفقیت ثبت شد!\n\n"
                f"📢 شناسه: {channel_id}\n"
                f"📛 عنوان: {channel_title or 'نامشخص'}\n"
                f"📝 نام کاربری: {channel_username or 'ندارد'}\n\n"
                f"🔒 کاربران برای استفاده از ربات باید در این کانال عضو باشند.",
                reply_markup=get_back_keyboard("admin_required_channels")
            )
            await state.clear()
            
    except Exception as e:
        logger.error(f"Error adding required channel: {e}")
        await message.answer(
            "❌ خطا در ثبت کانال اجباری.",
            reply_markup=get_back_keyboard("admin_required_channels")
        )
        await state.clear()

@router.callback_query(F.data.startswith("admin_required_channel_"))
async def admin_required_channel_detail(callback: CallbackQuery):
    """Show required channel detail"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    channel_id = int(callback.data.split("_")[3])
    
    try:
        async with AsyncSessionLocal() as session:
            channel = await session.get(RequiredChannel, channel_id)
            
            if not channel:
                await callback.answer("❌ کانال یافت نشد.")
                return
            
            text = f"🔒 <b>جزئیات کانال اجباری</b>\n\n"
            text += f"🆔 شناسه: {channel.channel_id}\n"
            text += f"📛 عنوان: {channel.channel_title or 'نامشخص'}\n"
            text += f"📝 نام کاربری: {channel.channel_username or 'ندارد'}\n"
            text += f"📊 وضعیت: {'🟢 فعال' if channel.is_active else '🔴 غیرفعال'}\n"
            text += f"📅 تاریخ ثبت: {channel.created_at.strftime('%Y-%m-%d %H:%M')}"
            
            await callback.message.edit_text(
                text,
                reply_markup=get_channel_edit_keyboard(channel.id),
                parse_mode="HTML"
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in admin_required_channel_detail: {e}")
        await callback.answer("❌ خطا در دریافت جزئیات کانال.")

@router.callback_query(F.data.startswith("delete_required_channel_"))
async def delete_required_channel(callback: CallbackQuery):
    """Delete required channel"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    channel_id = int(callback.data.split("_")[3])
    
    try:
        async with AsyncSessionLocal() as session:
            channel = await session.get(RequiredChannel, channel_id)
            
            if not channel:
                await callback.answer("❌ کانال یافت نشد.")
                return
            
            await session.delete(channel)
            await session.commit()
            
            await callback.message.edit_text(
                f"✅ کانال اجباری با موفقیت حذف شد.",
                reply_markup=get_back_keyboard("admin_required_channels")
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error deleting required channel: {e}")
        await callback.message.edit_text(
            "❌ خطا در حذف کانال اجباری.",
            reply_markup=get_back_keyboard("admin_required_channels")
        )
        await callback.answer()

@router.callback_query(F.data.startswith("toggle_required_channel_"))
async def toggle_required_channel(callback: CallbackQuery):
    """Toggle required channel active status"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    channel_id = int(callback.data.split("_")[3])
    
    try:
        async with AsyncSessionLocal() as session:
            channel = await session.get(RequiredChannel, channel_id)
            
            if not channel:
                await callback.answer("❌ کانال یافت نشد.")
                return
            
            channel.is_active = not channel.is_active
            await session.commit()
            
            status = "فعال" if channel.is_active else "غیرفعال"
            await callback.message.edit_text(
                f"✅ وضعیت کانال به '{status}' تغییر یافت.",
                reply_markup=get_back_keyboard("admin_required_channels")
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error toggling required channel: {e}")
        await callback.message.edit_text(
            "❌ خطا در تغییر وضعیت کانال.",
            reply_markup=get_back_keyboard("admin_required_channels")
        )
        await callback.answer()

@router.callback_query(F.data == "admin_edit_channel")
async def admin_edit_channel(callback: CallbackQuery, state: FSMContext):
    """Start edit sales channel"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    await callback.message.edit_text(
        "✏️ ویرایش کانال فروش:\n\n"
        "لطفاً شناسه جدید کانال را وارد کنید:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(SettingsStates.waiting_for_edit_channel_id)
    await callback.answer()

@router.message(SettingsStates.waiting_for_edit_channel_id, F.text)
async def handle_edit_channel_id(message: Message, state: FSMContext):
    """Handle edit sales channel"""
    channel_id = message.text.strip()
    
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(SalesChannel).where(SalesChannel.is_active == True)
            )
            channel = result.scalar_one_or_none()
            
            if channel:
                channel.channel_id = channel_id
            else:
                channel = SalesChannel(channel_id=channel_id)
                session.add(channel)
            
            await session.commit()
            
            await message.answer(
                f"✅ کانال فروش با موفقیت به‌روزرسانی شد.\n\n"
                f"📢 شناسه کانال: {channel_id}",
                reply_markup=get_back_keyboard("admin_channel")
            )
            await state.clear()
            
    except Exception as e:
        logger.error(f"Error editing channel: {e}")
        await message.answer(
            "❌ خطا در ویرایش کانال.",
            reply_markup=get_back_keyboard("admin_channel")
        )
        await state.clear()

@router.callback_query(F.data == "admin_delete_channel")
async def admin_delete_channel(callback: CallbackQuery):
    """Delete sales channel"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(SalesChannel).where(SalesChannel.is_active == True)
            )
            channel = result.scalar_one_or_none()
            
            if channel:
                await session.delete(channel)
                await session.commit()
                await callback.message.edit_text(
                    "✅ کانال فروش با موفقیت حذف شد.",
                    reply_markup=get_back_keyboard("admin_channel")
                )
            else:
                await callback.message.edit_text(
                    "❌ هیچ کانالی برای حذف وجود ندارد.",
                    reply_markup=get_back_keyboard("admin_channel")
                )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error deleting channel: {e}")
        await callback.message.edit_text(
            "❌ خطا در حذف کانال.",
            reply_markup=get_back_keyboard("admin_channel")
        )
        await callback.answer()