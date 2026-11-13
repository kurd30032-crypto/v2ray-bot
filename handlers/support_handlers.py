from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select  # <-- این خط را اضافه کنید
import logging

from keyboards.keyboards import (
    get_tickets_keyboard,
    get_ticket_detail_keyboard,
    get_back_keyboard,
    get_cancel_keyboard
)
from database.database import AsyncSessionLocal
from models.models import User, Ticket, Message as TicketMessage
from config import config

router = Router()
logger = logging.getLogger(__name__)

class TicketStates(StatesGroup):
    waiting_for_ticket_subject = State()
    waiting_for_ticket_message = State()
    waiting_for_ticket_reply = State()

@router.callback_query(F.data == "new_ticket")
async def new_ticket(callback: CallbackQuery, state: FSMContext):
    """Start new ticket creation"""
    await callback.message.edit_text(
        "📝 ایجاد تیکت جدید:\n\n"
        "لطفاً موضوع تیکت را وارد کنید:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(TicketStates.waiting_for_ticket_subject)
    await callback.answer()

@router.message(TicketStates.waiting_for_ticket_subject, F.text)
async def handle_ticket_subject(message: Message, state: FSMContext):
    """Handle ticket subject"""
    await state.update_data(ticket_subject=message.text)
    
    await message.answer(
        "💬 لطفاً متن پیام خود را وارد کنید:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(TicketStates.waiting_for_ticket_message)

@router.message(TicketStates.waiting_for_ticket_message, F.text)
async def handle_ticket_message(message: Message, state: FSMContext):
    """Handle ticket message"""
    data = await state.get_data()
    subject = data.get('ticket_subject')
    text = message.text
    
    try:
        async with AsyncSessionLocal() as session:
            # Get user
            result = await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                await message.answer(
                    "❌ کاربر یافت نشد.",
                    reply_markup=get_back_keyboard()
                )
                await state.clear()
                return
            
            # Create ticket
            ticket = Ticket(
                user_id=user.id,
                subject=subject
            )
            session.add(ticket)
            await session.commit()
            await session.refresh(ticket)
            
            # Create first message
            ticket_message = TicketMessage(
                ticket_id=ticket.id,
                user_id=user.id,
                message_text=text,
                is_from_user=True
            )
            session.add(ticket_message)
            await session.commit()
            
            # Notify admins
            for admin_id in config.ADMIN_IDS:
                try:
                    await message.bot.send_message(
                        admin_id,
                        f"💬 تیکت جدید!\n\n"
                        f"🆔 شماره تیکت: #{ticket.id}\n"
                        f"👤 کاربر: {user.first_name or user.username or user.telegram_id}\n"
                        f"📝 موضوع: {subject}\n"
                        f"💬 پیام: {text[:200]}{'...' if len(text) > 200 else ''}\n\n"
                        f"برای پاسخ، روی دکمه زیر کلیک کنید.",
                        reply_markup=get_ticket_detail_keyboard(ticket.id)
                    )
                except Exception as e:
                    logger.error(f"Error notifying admin about new ticket: {e}")
            
            await message.answer(
                f"✅ تیکت شما با موفقیت ایجاد شد!\n\n"
                f"🆔 شماره تیکت: #{ticket.id}\n"
                f"📝 موضوع: {subject}\n\n"
                f"🔔 ادمین‌ها از پیام شما مطلع شدند.\n"
                f"📋 برای مشاهده پاسخ، به بخش پشتیبانی مراجعه کنید.",
                reply_markup=get_back_keyboard("support")
            )
            await state.clear()
            
    except Exception as e:
        logger.error(f"Error creating ticket: {e}")
        await message.answer(
            "❌ خطا در ایجاد تیکت.",
            reply_markup=get_back_keyboard("support")
        )
        await state.clear()

@router.callback_query(F.data.startswith("ticket_detail_"))
async def ticket_detail(callback: CallbackQuery):
    """Show ticket detail"""
    ticket_id = int(callback.data.split("_")[2])
    
    try:
        async with AsyncSessionLocal() as session:
            ticket = await session.get(Ticket, ticket_id)
            
            if not ticket:
                await callback.answer("❌ تیکت یافت نشد.")
                return
            
            # Check if user owns this ticket or is admin
            result = await session.execute(
                select(User).where(User.telegram_id == callback.from_user.id)
            )
            user = result.scalar_one_or_none()
            
            is_admin = callback.from_user.id in config.ADMIN_IDS
            
            if not is_admin and (not user or ticket.user_id != user.id):
                await callback.answer("❌ شما به این تیکت دسترسی ندارید.")
                return
            
            # Get messages
            result = await session.execute(
                select(TicketMessage)
                .where(TicketMessage.ticket_id == ticket.id)
                .order_by(TicketMessage.created_at.asc())
            )
            messages = result.scalars().all()
            
            text = f"💬 تیکت #{ticket.id}\n"
            text += f"📝 موضوع: {ticket.subject}\n"
            text += f"📊 وضعیت: {'🟢 باز' if ticket.status.value == 'open' else '🔴 بسته'}\n"
            text += f"📅 تاریخ: {ticket.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
            text += "💬 پیام‌ها:\n"
            text += "─" * 30 + "\n"
            
            for msg in messages[-10:]:  # Show last 10 messages
                sender = "👤 شما" if msg.is_from_user else "👤 ادمین"
                text += f"{sender}:\n{msg.message_text}\n\n"
            
            await callback.message.edit_text(
                text,
                reply_markup=get_ticket_detail_keyboard(ticket_id)
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in ticket_detail: {e}")
        await callback.answer("❌ خطا در دریافت جزئیات تیکت.")

@router.callback_query(F.data.startswith("reply_ticket_"))
async def reply_ticket_start(callback: CallbackQuery, state: FSMContext):
    """Start reply to ticket"""
    ticket_id = int(callback.data.split("_")[2])
    await state.update_data(reply_ticket_id=ticket_id)
    
    await callback.message.edit_text(
        "✏️ پاسخ به تیکت:\n\n"
        "لطفاً متن پاسخ را وارد کنید:",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(TicketStates.waiting_for_ticket_reply)
    await callback.answer()

@router.message(TicketStates.waiting_for_ticket_reply, F.text)
async def handle_ticket_reply(message: Message, state: FSMContext):
    """Handle ticket reply"""
    data = await state.get_data()
    ticket_id = data.get('reply_ticket_id')
    text = message.text
    
    try:
        async with AsyncSessionLocal() as session:
            ticket = await session.get(Ticket, ticket_id)
            
            if not ticket:
                await message.answer(
                    "❌ تیکت یافت نشد.",
                    reply_markup=get_back_keyboard("support")
                )
                await state.clear()
                return
            
            # Get user
            result = await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                await message.answer(
                    "❌ کاربر یافت نشد.",
                    reply_markup=get_back_keyboard("support")
                )
                await state.clear()
                return
            
            is_admin = message.from_user.id in config.ADMIN_IDS
            
            # Create message
            ticket_message = TicketMessage(
                ticket_id=ticket.id,
                user_id=user.id,
                message_text=text,
                is_from_user=not is_admin
            )
            session.add(ticket_message)
            
            # Update ticket status
            if is_admin:
                ticket.status = "answered"
            else:
                ticket.status = "open"
            
            await session.commit()
            
            # Notify the other party
            if is_admin:
                # Send to user
                try:
                    await message.bot.send_message(
                        ticket.user.telegram_id,
                        f"💬 پاسخ ادمین به تیکت #{ticket.id}:\n\n"
                        f"{text}\n\n"
                        f"برای مشاهده تیکت، به بخش پشتیبانی مراجعه کنید.",
                        reply_markup=get_back_keyboard("support")
                    )
                except Exception as e:
                    logger.error(f"Error sending reply to user: {e}")
                
                await message.answer(
                    "✅ پاسخ شما با موفقیت به کاربر ارسال شد.",
                    reply_markup=get_back_keyboard("admin_panel")
                )
            else:
                # Notify admins
                for admin_id in config.ADMIN_IDS:
                    try:
                        await message.bot.send_message(
                            admin_id,
                            f"💬 پاسخ جدید در تیکت #{ticket.id}:\n\n"
                            f"👤 کاربر: {user.first_name or user.username or user.telegram_id}\n"
                            f"💬 پیام: {text[:200]}{'...' if len(text) > 200 else ''}\n\n"
                            f"برای پاسخ، روی دکمه زیر کلیک کنید.",
                            reply_markup=get_ticket_detail_keyboard(ticket.id)
                        )
                    except Exception as e:
                        logger.error(f"Error notifying admin about reply: {e}")
                
                await message.answer(
                    "✅ پاسخ شما با موفقیت ارسال شد.\n"
                    "🔔 ادمین‌ها از پاسخ شما مطلع شدند.",
                    reply_markup=get_back_keyboard("support")
                )
            
            await state.clear()
            
    except Exception as e:
        logger.error(f"Error in handle_ticket_reply: {e}")
        await message.answer(
            "❌ خطا در ارسال پاسخ.",
            reply_markup=get_back_keyboard("support")
        )
        await state.clear()

@router.callback_query(F.data.startswith("close_ticket_"))
async def close_ticket(callback: CallbackQuery):
    """Close ticket"""
    ticket_id = int(callback.data.split("_")[2])
    
    try:
        async with AsyncSessionLocal() as session:
            ticket = await session.get(Ticket, ticket_id)
            
            if not ticket:
                await callback.answer("❌ تیکت یافت نشد.")
                return
            
            ticket.status = "closed"
            await session.commit()
            
            await callback.message.edit_text(
                f"✅ تیکت #{ticket.id} با موفقیت بسته شد.",
                reply_markup=get_back_keyboard("support")
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in close_ticket: {e}")
        await callback.answer("❌ خطا در بستن تیکت.")

@router.callback_query(F.data == "cancel_action")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    """Cancel current action"""
    await state.clear()
    await callback.message.edit_text(
        "❌ عملیات لغو شد.",
        reply_markup=get_back_keyboard()
    )
    await callback.answer()