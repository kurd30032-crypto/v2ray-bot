from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
import logging

from keyboards.keyboards import (
    get_admin_cards_keyboard,
    get_card_edit_keyboard,
    get_back_keyboard,
    get_cancel_keyboard
)
from database.database import AsyncSessionLocal
from models.models import BankCard
from config import config

router = Router()
logger = logging.getLogger(__name__)

class CardStates(StatesGroup):
    waiting_for_card_holder = State()
    waiting_for_card_number = State()
    waiting_for_bank_name = State()
    waiting_for_edit_card_holder = State()
    waiting_for_edit_card_number = State()
    waiting_for_edit_bank_name = State()

# Admin filter
def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS

@router.callback_query(F.data == "admin_cards")
async def admin_cards(callback: CallbackQuery):
    """Show admin bank cards management"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(BankCard).order_by(BankCard.created_at.desc())
            )
            cards = result.scalars().all()
            
            await callback.message.edit_text(
                "💳 مدیریت کارت‌های بانکی:\n\n"
                "کارت‌های بانکی موجود را مشاهده و مدیریت کنید.",
                reply_markup=get_admin_cards_keyboard(cards)
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in admin_cards: {e}")
        await callback.message.edit_text(
            "❌ خطا در دریافت کارت‌های بانکی.",
            reply_markup=get_back_keyboard("admin_panel")
        )
        await callback.answer()

@router.callback_query(F.data == "admin_add_card")
async def admin_add_card(callback: CallbackQuery, state: FSMContext):
    """Start add card process"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    await callback.message.edit_text(
        "➕ افزودن کارت بانکی جدید:\n\n"
        "👤 لطفاً نام دارنده کارت را وارد کنید:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(CardStates.waiting_for_card_holder)
    await callback.answer()

@router.message(CardStates.waiting_for_card_holder, F.text)
async def handle_card_holder(message: Message, state: FSMContext):
    """Handle card holder name"""
    await state.update_data(card_holder=message.text)
    
    await message.answer(
        "🔢 لطفاً شماره کارت (۱۶ رقمی) را وارد کنید:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(CardStates.waiting_for_card_number)

@router.message(CardStates.waiting_for_card_number, F.text)
async def handle_card_number(message: Message, state: FSMContext):
    """Handle card number"""
    card_number = message.text.replace(' ', '').replace('-', '')
    
    if len(card_number) != 16 or not card_number.isdigit():
        await message.answer(
            "❌ شماره کارت باید ۱۶ رقم باشد. لطفاً دوباره وارد کنید:",
            reply_markup=get_cancel_keyboard()
        )
        return
    
    await state.update_data(card_number=card_number)
    
    await message.answer(
        "🏦 لطفاً نام بانک را وارد کنید:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(CardStates.waiting_for_bank_name)

@router.message(CardStates.waiting_for_bank_name, F.text)
async def handle_bank_name(message: Message, state: FSMContext):
    """Handle bank name"""
    await state.update_data(bank_name=message.text)
    
    data = await state.get_data()
    
    try:
        async with AsyncSessionLocal() as session:
            card = BankCard(
                card_holder=data['card_holder'],
                card_number=data['card_number'],
                bank_name=data['bank_name']
            )
            session.add(card)
            await session.commit()
            
            await message.answer(
                f"✅ کارت بانکی با موفقیت افزوده شد!\n\n"
                f"👤 دارنده: {card.card_holder}\n"
                f"🔢 شماره: {card.card_number}\n"
                f"🏦 بانک: {card.bank_name}",
                reply_markup=get_back_keyboard("admin_cards")
            )
            await state.clear()
            
    except Exception as e:
        logger.error(f"Error creating bank card: {e}")
        await message.answer(
            "❌ خطا در افزودن کارت بانکی.",
            reply_markup=get_back_keyboard("admin_cards")
        )
        await state.clear()

@router.callback_query(F.data.startswith("admin_card_"))
async def admin_card_detail(callback: CallbackQuery):
    """Show card detail"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    card_id = int(callback.data.split("_")[2])
    
    try:
        async with AsyncSessionLocal() as session:
            card = await session.get(BankCard, card_id)
            
            if not card:
                await callback.answer("❌ کارت یافت نشد.")
                return
            
            status_emoji = "🟢" if card.is_active else "🔴"
            
            text = f"💳 جزئیات کارت بانکی:\n\n"
            text += f"👤 دارنده: {card.card_holder}\n"
            text += f"🔢 شماره: {card.card_number}\n"
            text += f"🏦 بانک: {card.bank_name}\n"
            text += f"📊 وضعیت: {status_emoji}\n"
            text += f"📅 تاریخ ایجاد: {card.created_at.strftime('%Y-%m-%d %H:%M')}"
            
            await callback.message.edit_text(
                text,
                reply_markup=get_card_edit_keyboard(card_id)
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in admin_card_detail: {e}")
        await callback.answer("❌ خطا در دریافت جزئیات کارت.")

@router.callback_query(F.data.startswith("edit_card_"))
async def edit_card_start(callback: CallbackQuery, state: FSMContext):
    """Start card edit process"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    card_id = int(callback.data.split("_")[2])
    await state.update_data(edit_card_id=card_id)
    
    await callback.message.edit_text(
        "✏️ ویرایش کارت بانکی:\n\n"
        "👤 نام جدید دارنده را وارد کنید (برای حفظ مقدار فعلی، 'همان' را وارد کنید):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(CardStates.waiting_for_edit_card_holder)
    await callback.answer()

@router.message(CardStates.waiting_for_edit_card_holder, F.text)
async def handle_edit_card_holder(message: Message, state: FSMContext):
    """Handle edit card holder"""
    await state.update_data(edit_card_holder=message.text if message.text != "همان" else None)
    
    await message.answer(
        "🔢 شماره کارت جدید را وارد کنید (برای حفظ مقدار فعلی، 'همان' را وارد کنید):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(CardStates.waiting_for_edit_card_number)

@router.message(CardStates.waiting_for_edit_card_number, F.text)
async def handle_edit_card_number(message: Message, state: FSMContext):
    """Handle edit card number"""
    if message.text != "همان":
        card_number = message.text.replace(' ', '').replace('-', '')
        if len(card_number) != 16 or not card_number.isdigit():
            await message.answer(
                "❌ شماره کارت باید ۱۶ رقم باشد. لطفاً دوباره وارد کنید:",
                reply_markup=get_cancel_keyboard()
            )
            return
        await state.update_data(edit_card_number=card_number)
    else:
        await state.update_data(edit_card_number=None)
    
    await message.answer(
        "🏦 نام بانک جدید را وارد کنید (برای حفظ مقدار فعلی، 'همان' را وارد کنید):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(CardStates.waiting_for_edit_bank_name)

@router.message(CardStates.waiting_for_edit_bank_name, F.text)
async def handle_edit_bank_name(message: Message, state: FSMContext):
    """Handle edit bank name"""
    await state.update_data(edit_bank_name=message.text if message.text != "همان" else None)
    
    data = await state.get_data()
    card_id = data.get('edit_card_id')
    
    try:
        async with AsyncSessionLocal() as session:
            card = await session.get(BankCard, card_id)
            
            if not card:
                await message.answer(
                    "❌ کارت یافت نشد.",
                    reply_markup=get_back_keyboard("admin_cards")
                )
                await state.clear()
                return
            
            if data.get('edit_card_holder') is not None:
                card.card_holder = data['edit_card_holder']
            if data.get('edit_card_number') is not None:
                card.card_number = data['edit_card_number']
            if data.get('edit_bank_name') is not None:
                card.bank_name = data['edit_bank_name']
            
            await session.commit()
            
            await message.answer(
                f"✅ کارت بانکی با موفقیت ویرایش شد!",
                reply_markup=get_back_keyboard("admin_cards")
            )
            await state.clear()
            
    except Exception as e:
        logger.error(f"Error editing card: {e}")
        await message.answer(
            "❌ خطا در ویرایش کارت بانکی.",
            reply_markup=get_back_keyboard("admin_cards")
        )
        await state.clear()

@router.callback_query(F.data.startswith("delete_card_"))
async def delete_card(callback: CallbackQuery):
    """Delete bank card"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    card_id = int(callback.data.split("_")[2])
    
    try:
        async with AsyncSessionLocal() as session:
            card = await session.get(BankCard, card_id)
            
            if not card:
                await callback.answer("❌ کارت یافت نشد.")
                return
            
            await session.delete(card)
            await session.commit()
            
            await callback.message.edit_text(
                f"✅ کارت بانکی با موفقیت حذف شد.",
                reply_markup=get_back_keyboard("admin_cards")
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error deleting card: {e}")
        await callback.message.edit_text(
            "❌ خطا در حذف کارت بانکی.",
            reply_markup=get_back_keyboard("admin_cards")
        )
        await callback.answer()

@router.callback_query(F.data.startswith("toggle_card_"))
async def toggle_card(callback: CallbackQuery):
    """Toggle card active status"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    card_id = int(callback.data.split("_")[2])
    
    try:
        async with AsyncSessionLocal() as session:
            card = await session.get(BankCard, card_id)
            
            if not card:
                await callback.answer("❌ کارت یافت نشد.")
                return
            
            card.is_active = not card.is_active
            await session.commit()
            
            status = "فعال" if card.is_active else "غیرفعال"
            await callback.message.edit_text(
                f"✅ وضعیت کارت بانکی به '{status}' تغییر یافت.",
                reply_markup=get_back_keyboard("admin_cards")
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error toggling card: {e}")
        await callback.message.edit_text(
            "❌ خطا در تغییر وضعیت کارت بانکی.",
            reply_markup=get_back_keyboard("admin_cards")
        )
        await callback.answer()