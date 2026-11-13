from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
import logging

from keyboards.keyboards import (
    get_admin_plans_keyboard,
    get_plan_edit_keyboard,
    get_back_keyboard,
    get_cancel_keyboard
)
from database.database import AsyncSessionLocal
from models.models import Plan
from config import config

router = Router()
logger = logging.getLogger(__name__)

class PlanStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_volume = State()
    waiting_for_duration = State()
    waiting_for_price = State()
    waiting_for_description = State()
    waiting_for_edit_name = State()
    waiting_for_edit_volume = State()
    waiting_for_edit_duration = State()
    waiting_for_edit_price = State()
    waiting_for_edit_description = State()

# Admin filter
def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS

@router.callback_query(F.data == "admin_plans")
async def admin_plans(callback: CallbackQuery):
    """Show admin plans management"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Plan).order_by(Plan.created_at.desc())
            )
            plans = result.scalars().all()
            
            await callback.message.edit_text(
                "📋 مدیریت تعرفه‌ها:\n\n"
                "تعرفه‌های موجود را مشاهده و مدیریت کنید.",
                reply_markup=get_admin_plans_keyboard(plans)
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in admin_plans: {e}")
        await callback.message.edit_text(
            "❌ خطا در دریافت تعرفه‌ها.",
            reply_markup=get_back_keyboard("admin_panel")
        )
        await callback.answer()

@router.callback_query(F.data == "admin_add_plan")
async def admin_add_plan(callback: CallbackQuery, state: FSMContext):
    """Start add plan process"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    await callback.message.edit_text(
        "➕ افزودن تعرفه جدید:\n\n"
        "📛 لطفاً نام تعرفه را وارد کنید:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(PlanStates.waiting_for_name)
    await callback.answer()

@router.message(PlanStates.waiting_for_name, F.text)
async def handle_plan_name(message: Message, state: FSMContext):
    """Handle plan name"""
    await state.update_data(name=message.text)
    
    await message.answer(
        "💾 لطفاً حجم سرویس را وارد کنید (مثلاً: 10GB):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(PlanStates.waiting_for_volume)

@router.message(PlanStates.waiting_for_volume, F.text)
async def handle_plan_volume(message: Message, state: FSMContext):
    """Handle plan volume"""
    await state.update_data(volume=message.text)
    
    await message.answer(
        "⏰ لطفاً مدت زمان را وارد کنید (مثلاً: 30 روز، 1 ماه، 1 سال):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(PlanStates.waiting_for_duration)

@router.message(PlanStates.waiting_for_duration, F.text)
async def handle_plan_duration(message: Message, state: FSMContext):
    """Handle plan duration"""
    await state.update_data(duration=message.text)
    
    await message.answer(
        "💰 لطفاً قیمت را به تومان وارد کنید (مثلاً: 150000):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(PlanStates.waiting_for_price)

@router.message(PlanStates.waiting_for_price, F.text)
async def handle_plan_price(message: Message, state: FSMContext):
    """Handle plan price"""
    try:
        price = float(message.text.replace(',', '').strip())
        await state.update_data(price=price)
        
        await message.answer(
            "📝 لطفاً توضیحات تعرفه را وارد کنید (اختیاری - برای رد کردن 'بدون توضیحات' را ارسال کنید):",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(PlanStates.waiting_for_description)
        
    except ValueError:
        await message.answer(
            "❌ قیمت باید عدد باشد. لطفاً دوباره وارد کنید:",
            reply_markup=get_cancel_keyboard()
        )

@router.message(PlanStates.waiting_for_description, F.text)
async def handle_plan_description(message: Message, state: FSMContext):
    """Handle plan description"""
    description = message.text if message.text != "بدون توضیحات" else None
    await state.update_data(description=description)
    
    data = await state.get_data()
    
    try:
        async with AsyncSessionLocal() as session:
            plan = Plan(
                name=data['name'],
                volume=data['volume'],
                duration=data['duration'],
                price=data['price'],
                description=data.get('description')
            )
            session.add(plan)
            await session.commit()
            
            await message.answer(
                f"✅ تعرفه '{plan.name}' با موفقیت ایجاد شد!\n\n"
                f"📛 نام: {plan.name}\n"
                f"💾 حجم: {plan.volume}\n"
                f"⏰ مدت: {plan.duration}\n"
                f"💰 قیمت: {format_price(plan.price)} تومان\n"
                f"📝 توضیحات: {plan.description or 'بدون توضیحات'}",
                reply_markup=get_back_keyboard("admin_plans")
            )
            await state.clear()
            
    except Exception as e:
        logger.error(f"Error creating plan: {e}")
        await message.answer(
            "❌ خطا در ایجاد تعرفه.",
            reply_markup=get_back_keyboard("admin_plans")
        )
        await state.clear()

@router.callback_query(F.data.startswith("admin_plan_"))
async def admin_plan_detail(callback: CallbackQuery):
    """Show plan detail"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    plan_id = int(callback.data.split("_")[2])
    
    try:
        async with AsyncSessionLocal() as session:
            plan = await session.get(Plan, plan_id)
            
            if not plan:
                await callback.answer("❌ تعرفه یافت نشد.")
                return
            
            status_emoji = "🟢" if plan.is_active else "🔴"
            
            text = f"📋 جزئیات تعرفه:\n\n"
            text += f"📛 نام: {plan.name}\n"
            text += f"💾 حجم: {plan.volume}\n"
            text += f"⏰ مدت: {plan.duration}\n"
            text += f"💰 قیمت: {format_price(plan.price)} تومان\n"
            text += f"📝 توضیحات: {plan.description or 'بدون توضیحات'}\n"
            text += f"📊 وضعیت: {status_emoji}\n"
            text += f"📅 تاریخ ایجاد: {plan.created_at.strftime('%Y-%m-%d %H:%M')}"
            
            await callback.message.edit_text(
                text,
                reply_markup=get_plan_edit_keyboard(plan_id)
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in admin_plan_detail: {e}")
        await callback.answer("❌ خطا در دریافت جزئیات تعرفه.")

@router.callback_query(F.data.startswith("edit_plan_"))
async def edit_plan_start(callback: CallbackQuery, state: FSMContext):
    """Start plan edit process"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    plan_id = int(callback.data.split("_")[2])
    await state.update_data(edit_plan_id=plan_id)
    
    await callback.message.edit_text(
        "✏️ ویرایش تعرفه:\n\n"
        "لطفاً نام جدید را وارد کنید (برای حفظ مقدار فعلی، 'همان' را وارد کنید):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(PlanStates.waiting_for_edit_name)
    await callback.answer()

@router.message(PlanStates.waiting_for_edit_name, F.text)
async def handle_edit_plan_name(message: Message, state: FSMContext):
    """Handle edit plan name"""
    await state.update_data(edit_name=message.text if message.text != "همان" else None)
    
    await message.answer(
        "💾 حجم جدید را وارد کنید (برای حفظ مقدار فعلی، 'همان' را وارد کنید):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(PlanStates.waiting_for_edit_volume)

@router.message(PlanStates.waiting_for_edit_volume, F.text)
async def handle_edit_plan_volume(message: Message, state: FSMContext):
    """Handle edit plan volume"""
    await state.update_data(edit_volume=message.text if message.text != "همان" else None)
    
    await message.answer(
        "⏰ مدت جدید را وارد کنید (برای حفظ مقدار فعلی، 'همان' را وارد کنید):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(PlanStates.waiting_for_edit_duration)

@router.message(PlanStates.waiting_for_edit_duration, F.text)
async def handle_edit_plan_duration(message: Message, state: FSMContext):
    """Handle edit plan duration"""
    await state.update_data(edit_duration=message.text if message.text != "همان" else None)
    
    await message.answer(
        "💰 قیمت جدید را به تومان وارد کنید (برای حفظ مقدار فعلی، 'همان' را وارد کنید):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(PlanStates.waiting_for_edit_price)

@router.message(PlanStates.waiting_for_edit_price, F.text)
async def handle_edit_plan_price(message: Message, state: FSMContext):
    """Handle edit plan price"""
    try:
        if message.text != "همان":
            price = float(message.text.replace(',', '').strip())
            await state.update_data(edit_price=price)
        else:
            await state.update_data(edit_price=None)
        
        await message.answer(
            "📝 توضیحات جدید را وارد کنید (برای حفظ مقدار فعلی 'همان'، برای حذف 'حذف' را وارد کنید):",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(PlanStates.waiting_for_edit_description)
        
    except ValueError:
        await message.answer(
            "❌ قیمت باید عدد باشد. لطفاً دوباره وارد کنید:",
            reply_markup=get_cancel_keyboard()
        )

@router.message(PlanStates.waiting_for_edit_description, F.text)
async def handle_edit_plan_description(message: Message, state: FSMContext):
    """Handle edit plan description"""
    if message.text == "حذف":
        await state.update_data(edit_description="DELETE")
    elif message.text == "همان":
        await state.update_data(edit_description=None)
    else:
        await state.update_data(edit_description=message.text)
    
    data = await state.get_data()
    plan_id = data.get('edit_plan_id')
    
    try:
        async with AsyncSessionLocal() as session:
            plan = await session.get(Plan, plan_id)
            
            if not plan:
                await message.answer(
                    "❌ تعرفه یافت نشد.",
                    reply_markup=get_back_keyboard("admin_plans")
                )
                await state.clear()
                return
            
            # Update fields
            if data.get('edit_name') is not None:
                plan.name = data['edit_name']
            if data.get('edit_volume') is not None:
                plan.volume = data['edit_volume']
            if data.get('edit_duration') is not None:
                plan.duration = data['edit_duration']
            if data.get('edit_price') is not None:
                plan.price = data['edit_price']
            if data.get('edit_description') == "DELETE":
                plan.description = None
            elif data.get('edit_description') is not None:
                plan.description = data['edit_description']
            
            await session.commit()
            
            await message.answer(
                f"✅ تعرفه '{plan.name}' با موفقیت ویرایش شد!",
                reply_markup=get_back_keyboard("admin_plans")
            )
            await state.clear()
            
    except Exception as e:
        logger.error(f"Error editing plan: {e}")
        await message.answer(
            "❌ خطا در ویرایش تعرفه.",
            reply_markup=get_back_keyboard("admin_plans")
        )
        await state.clear()

@router.callback_query(F.data.startswith("delete_plan_"))
async def delete_plan(callback: CallbackQuery):
    """Delete plan"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    plan_id = int(callback.data.split("_")[2])
    
    try:
        async with AsyncSessionLocal() as session:
            plan = await session.get(Plan, plan_id)
            
            if not plan:
                await callback.answer("❌ تعرفه یافت نشد.")
                return
            
            await session.delete(plan)
            await session.commit()
            
            await callback.message.edit_text(
                f"✅ تعرفه '{plan.name}' با موفقیت حذف شد.",
                reply_markup=get_back_keyboard("admin_plans")
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error deleting plan: {e}")
        await callback.message.edit_text(
            "❌ خطا در حذف تعرفه.",
            reply_markup=get_back_keyboard("admin_plans")
        )
        await callback.answer()

@router.callback_query(F.data.startswith("toggle_plan_"))
async def toggle_plan(callback: CallbackQuery):
    """Toggle plan active status"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    plan_id = int(callback.data.split("_")[2])
    
    try:
        async with AsyncSessionLocal() as session:
            plan = await session.get(Plan, plan_id)
            
            if not plan:
                await callback.answer("❌ تعرفه یافت نشد.")
                return
            
            plan.is_active = not plan.is_active
            await session.commit()
            
            status = "فعال" if plan.is_active else "غیرفعال"
            await callback.message.edit_text(
                f"✅ وضعیت تعرفه '{plan.name}' به '{status}' تغییر یافت.",
                reply_markup=get_back_keyboard("admin_plans")
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error toggling plan: {e}")
        await callback.message.edit_text(
            "❌ خطا در تغییر وضعیت تعرفه.",
            reply_markup=get_back_keyboard("admin_plans")
        )
        await callback.answer()
        
        
        
def format_price(price):
    return f"{int(price):,}"