from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from sqlalchemy import select
from datetime import datetime, timedelta
import logging
import os
import re
import traceback
from sqlalchemy.orm import joinedload

from keyboards.keyboards import (
    get_plan_detail_keyboard,
    get_purchase_actions_keyboard,
    get_back_keyboard,
    get_cancel_keyboard,
    get_confirmation_keyboard
)
from database.database import AsyncSessionLocal
from models.models import User, Plan, Purchase, BankCard, Payment, Config, SalesChannel, PurchaseStatus, UserStatus
from config import config

router = Router()
logger = logging.getLogger(__name__)

class PurchaseStates(StatesGroup):
    waiting_for_receipt = State()
    waiting_for_rejection_reason = State()
    waiting_for_renew_plan = State()
    waiting_for_payment_confirm = State()

def format_price(price):
    """Format price with commas"""
    try:
        return f"{int(float(price)):,}"
    except:
        return str(price)

def parse_duration(duration_str):
    """Parse duration string and return days"""
    try:
        duration_str = str(duration_str).strip().lower()
        
        # Check if it contains 'روز'
        if 'روز' in duration_str:
            numbers = re.findall(r'\d+', duration_str)
            if numbers:
                return int(numbers[0])
        
        # Check if it contains 'ماه'
        if 'ماه' in duration_str:
            numbers = re.findall(r'\d+', duration_str)
            if numbers:
                return int(numbers[0]) * 30
        
        # Check if it contains 'سال'
        if 'سال' in duration_str:
            numbers = re.findall(r'\d+', duration_str)
            if numbers:
                return int(numbers[0]) * 365
        
        # If only number, assume days
        numbers = re.findall(r'\d+', duration_str)
        if numbers:
            return int(numbers[0])
        
        # Default to 30 days
        return 30
        
    except Exception as e:
        logger.error(f"Error parsing duration '{duration_str}': {e}")
        return 30

@router.callback_query(F.data.startswith("select_plan_"))
async def select_plan(callback: CallbackQuery):
    """Show selected plan details"""
    try:
        plan_id = int(callback.data.split("_")[2])
        
        async with AsyncSessionLocal() as session:
            plan = await session.get(Plan, plan_id)
            
            if not plan:
                await callback.answer("❌ تعرفه یافت نشد.")
                return
            
            text = f"📋 مشخصات تعرفه:\n\n"
            text += f"📛 نام: {plan.name}\n"
            text += f"💾 حجم: {plan.volume}\n"
            text += f"⏰ مدت: {plan.duration}\n"
            text += f"💰 قیمت: {format_price(plan.price)} تومان\n"
            text += f"📝 توضیحات: {plan.description or 'بدون توضیحات'}\n\n"
            text += "🛒 برای خرید روی دکمه زیر کلیک کنید."
            
            await callback.message.edit_text(
                text,
                reply_markup=get_plan_detail_keyboard(plan_id)
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in select_plan: {e}")
        await callback.message.edit_text(
            "❌ خطا در دریافت اطلاعات تعرفه.",
            reply_markup=get_back_keyboard("plans")
        )
        await callback.answer()

@router.callback_query(F.data.startswith("buy_plan_"))
async def buy_plan(callback: CallbackQuery, state: FSMContext):
    """Initiate purchase process - Show bank cards"""
    try:
        plan_id = int(callback.data.split("_")[2])
        
        async with AsyncSessionLocal() as session:
            # Check if user exists
            result = await session.execute(
                select(User).where(User.telegram_id == callback.from_user.id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                await callback.answer("❌ کاربر یافت نشد.")
                return
            
            if user.status != UserStatus.ACTIVE:
                await callback.answer("❌ حساب کاربری شما مسدود است.")
                return
            
            # Get the plan
            plan = await session.get(Plan, plan_id)
            if not plan:
                await callback.answer("❌ تعرفه یافت نشد.")
                return
            
            # Get active bank cards
            result = await session.execute(
                select(BankCard).where(BankCard.is_active == True)
            )
            cards = result.scalars().all()
            
            if not cards:
                await callback.message.edit_text(
                    "❌ در حال حاضر هیچ کارت بانکی برای پرداخت ثبت نشده است.\n"
                    "لطفاً بعداً تلاش کنید.",
                    reply_markup=get_back_keyboard("plans")
                )
                await callback.answer()
                return
            
            # Create purchase
            purchase = Purchase(
                user_id=user.id,
                plan_id=plan.id,
                amount=float(plan.price),
                status=PurchaseStatus.PENDING
            )
            session.add(purchase)
            await session.commit()
            await session.refresh(purchase)
            
            # Store purchase_id in state
            await state.update_data(purchase_id=purchase.id)
            await state.update_data(plan_name=plan.name)
            await state.update_data(plan_price=float(plan.price))
            
            # Show payment instructions with bank cards
            card_text = "💳 شماره کارت‌های بانکی برای واریز:\n\n"
            for idx, card in enumerate(cards, 1):
                card_text += f"🏦 {idx}. بانک {card.bank_name}\n"
                card_text += f"   👤 دارنده: {card.card_holder}\n"
                card_text += f"   🔢 شماره کارت: <code>{card.card_number}</code>\n\n"
            
            text = f"💰 مبلغ قابل پرداخت: <b>{format_price(plan.price)}</b> تومان\n"
            text += f"📋 تعرفه: <b>{plan.name}</b>\n\n"
            text += "📤 لطفاً مبلغ را به یکی از کارت‌های زیر واریز کنید:\n\n"
            text += card_text
            text += "─────────────────────\n"
            text += "📸 <b>پس از واریز، رسید پرداخت را ارسال کنید.</b>\n\n"
            text += "⚠️ <b>توجه:</b>\n"
            text += "• رسید باید شامل تاریخ و مبلغ واریزی باشد.\n"
            text += "• حتماً شماره خرید خود را در رسید ذکر کنید.\n"
            text += "• پس از ارسال رسید، درخواست شما بررسی می‌شود."
            
            await callback.message.edit_text(
                text,
                reply_markup=get_cancel_keyboard(),
                parse_mode="HTML"
            )
            
            await state.set_state(PurchaseStates.waiting_for_receipt)
            await callback.answer("✅ لطفاً رسید پرداخت را ارسال کنید.")
            
    except Exception as e:
        logger.error(f"Error in buy_plan: {e}")
        logger.error(traceback.format_exc())
        await callback.message.edit_text(
            "❌ خطا در شروع فرآیند خرید.\n"
            "لطفاً دوباره تلاش کنید.",
            reply_markup=get_back_keyboard("plans")
        )
        await callback.answer()

@router.message(PurchaseStates.waiting_for_receipt, F.photo)
async def handle_receipt_photo(message: Message, state: FSMContext):
    """Handle receipt image upload"""
    try:
        data = await state.get_data()
        purchase_id = data.get('purchase_id')
        plan_name = data.get('plan_name', 'نامشخص')
        plan_price = data.get('plan_price', 0)
        
        if not purchase_id:
            await message.answer(
                "❌ خطا در یافتن خرید. لطفاً دوباره تلاش کنید.",
                reply_markup=get_back_keyboard()
            )
            await state.clear()
            return
        
        # Download photo
        photo = message.photo[-1]
        file = await message.bot.get_file(photo.file_id)
        file_path = f"receipts/receipt_{purchase_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        
        # Ensure directory exists
        os.makedirs("receipts", exist_ok=True)
        
        await message.bot.download_file(file.file_path, file_path)
        
        async with AsyncSessionLocal() as session:
            purchase = await session.get(Purchase, purchase_id)
            
            if not purchase:
                await message.answer(
                    "❌ خطا در یافتن خرید.",
                    reply_markup=get_back_keyboard()
                )
                await state.clear()
                return
            
            # Update purchase with receipt
            purchase.receipt_image = file_path
            await session.commit()
            
            # Get purchase with relations
            purchase = await session.get(Purchase, purchase_id)
            
            # Notify admins
            admin_notified = False
            for admin_id in config.ADMIN_IDS:
                try:
                    # Send receipt to admin
                    await message.bot.send_photo(
                        admin_id,
                        FSInputFile(file_path),
                        caption=f"📥 <b>درخواست خرید جدید!</b>\n\n"
                                f"🆔 شماره خرید: <code>#{purchase_id}</code>\n"
                                f"👤 کاربر: {message.from_user.first_name or 'نامشخص'}\n"
                                f"📝 نام کاربری: @{message.from_user.username or 'ندارد'}\n"
                                f"🆔 شناسه: <code>{message.from_user.id}</code>\n"
                                f"📋 تعرفه: <b>{plan_name}</b>\n"
                                f"💰 مبلغ: <b>{format_price(plan_price)}</b> تومان\n\n"
                                f"🖼️ رسید پرداخت ارسال شده است.\n"
                                f"⏳ در انتظار تایید...",
                        parse_mode="HTML",
                        reply_markup=get_purchase_actions_keyboard(purchase_id, is_admin=True)
                    )
                    admin_notified = True
                except Exception as e:
                    logger.error(f"Error notifying admin {admin_id}: {e}")
            
            await message.answer(
                "✅ <b>رسید شما با موفقیت ارسال شد!</b>\n\n"
                "📋 درخواست شما در انتظار تایید ادمین می‌باشد.\n"
                "🔔 پس از تایید، کانفیگ برای شما ارسال خواهد شد.\n\n"
                "⏱️ زمان بررسی: معمولاً کمتر از ۲۴ ساعت",
                reply_markup=get_back_keyboard("my_services"),
                parse_mode="HTML"
            )
            
            await state.clear()
            
    except Exception as e:
        logger.error(f"Error in handle_receipt_photo: {e}")
        await message.answer(
            "❌ خطا در ارسال رسید. لطفاً دوباره تلاش کنید.",
            reply_markup=get_back_keyboard()
        )
        await state.clear()

@router.message(PurchaseStates.waiting_for_receipt, F.text)
async def handle_receipt_text(message: Message, state: FSMContext):
    """Handle receipt text"""
    try:
        data = await state.get_data()
        purchase_id = data.get('purchase_id')
        plan_name = data.get('plan_name', 'نامشخص')
        plan_price = data.get('plan_price', 0)
        
        if not purchase_id:
            await message.answer(
                "❌ خطا در یافتن خرید. لطفاً دوباره تلاش کنید.",
                reply_markup=get_back_keyboard()
            )
            await state.clear()
            return
        
        receipt_text = message.text
        
        async with AsyncSessionLocal() as session:
            purchase = await session.get(Purchase, purchase_id)
            
            if not purchase:
                await message.answer(
                    "❌ خطا در یافتن خرید.",
                    reply_markup=get_back_keyboard()
                )
                await state.clear()
                return
            
            # Notify admins with text
            for admin_id in config.ADMIN_IDS:
                try:
                    await message.bot.send_message(
                        admin_id,
                        f"📥 <b>درخواست خرید جدید (متن)</b>\n\n"
                        f"🆔 شماره خرید: <code>#{purchase_id}</code>\n"
                        f"👤 کاربر: {message.from_user.first_name or 'نامشخص'}\n"
                        f"📝 نام کاربری: @{message.from_user.username or 'ندارد'}\n"
                        f"🆔 شناسه: <code>{message.from_user.id}</code>\n"
                        f"📋 تعرفه: <b>{plan_name}</b>\n"
                        f"💰 مبلغ: <b>{format_price(plan_price)}</b> تومان\n\n"
                        f"📝 <b>متن رسید:</b>\n{receipt_text}\n\n"
                        f"⏳ در انتظار تایید...",
                        parse_mode="HTML",
                        reply_markup=get_purchase_actions_keyboard(purchase_id, is_admin=True)
                    )
                except Exception as e:
                    logger.error(f"Error notifying admin {admin_id}: {e}")
            
            await message.answer(
                "✅ <b>رسید شما با موفقیت ارسال شد!</b>\n\n"
                "📋 درخواست شما در انتظار تایید ادمین می‌باشد.\n"
                "🔔 پس از تایید، کانفیگ برای شما ارسال خواهد شد.",
                reply_markup=get_back_keyboard("my_services"),
                parse_mode="HTML"
            )
            
            await state.clear()
            
    except Exception as e:
        logger.error(f"Error in handle_receipt_text: {e}")
        await message.answer(
            "❌ خطا در ارسال رسید. لطفاً دوباره تلاش کنید.",
            reply_markup=get_back_keyboard()
        )
        await state.clear()

@router.message(PurchaseStates.waiting_for_receipt)
async def handle_invalid_receipt(message: Message):
    """Handle invalid receipt input"""
    await message.answer(
        "❌ لطفاً یک <b>تصویر</b> از رسید پرداخت ارسال کنید.\n\n"
        "📸 روی دکمه <b>'آپلود عکس'</b> کلیک کرده و تصویر رسید را انتخاب کنید.\n"
        "یا اگر رسید به صورت متن است، می‌توانید متن را ارسال کنید.",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )

@router.callback_query(F.data.startswith("approve_purchase_"))
async def approve_purchase(callback: CallbackQuery):
    """Approve purchase and send config to user"""
    try:
        purchase_id = int(callback.data.split("_")[2])
        logger.info(f"Approving purchase: {purchase_id}")
        
        async with AsyncSessionLocal() as session:
            # اصلاح: بارگذاری با join
            result = await session.execute(
                select(Purchase)
                .options(joinedload(Purchase.plan))
                .options(joinedload(Purchase.user))
                .where(Purchase.id == purchase_id)
            )
            purchase = result.scalar_one_or_none()
            
            if not purchase:
                await callback.answer("❌ خرید یافت نشد.")
                return
            
            # Get an active config
            result = await session.execute(
                select(Config).where(Config.is_active == True)
            )
            configs = result.scalars().all()
            
            if not configs:
                await callback.message.answer(
                    "❌ هیچ کانفیگ فعالی موجود نیست.\n"
                    "لطفاً ابتدا یک کانفیگ اضافه کنید.",
                    reply_markup=get_back_keyboard("admin_purchases")
                )
                await callback.answer()
                return
            
            # Assign first active config
            config_obj = configs[0]
            purchase.config_id = config_obj.id
            
            # Calculate expiry date - حالا به راحتی کار می‌کند
            days = parse_duration(purchase.plan.duration)
            expiry_date = datetime.now() + timedelta(days=days)
            
            purchase.expiry_date = expiry_date
            purchase.status = PurchaseStatus.APPROVED
            
            # Create payment record
            payment = Payment(
                purchase_id=purchase.id,
                amount=purchase.amount,
                payment_date=datetime.now()
            )
            session.add(payment)
            
            await session.commit()
            logger.info(f"Purchase {purchase_id} approved successfully")
            
            # Send config to user
            try:
                config_text = f"🔐 <b>کانفیگ V2Ray شما</b>\n\n"
                config_text += f"📛 نام: {config_obj.name}\n"
                config_text += f"📋 تعرفه: {purchase.plan.name}\n"
                config_text += f"📅 تاریخ خرید: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                config_text += f"📅 تاریخ انقضا: {expiry_date.strftime('%Y-%m-%d %H:%M')}\n\n"
                config_text += f"<b>🔗 لینک کانفیگ:</b>\n"
                config_text += f"<code>{config_obj.address}</code>\n\n"
                config_text += "📱 برای راهنمای اتصال، به بخش 'راهنمای اتصال' مراجعه کنید."
                
                await callback.bot.send_message(
                    purchase.user.telegram_id,
                    config_text,
                    parse_mode="HTML"
                )
                
                await callback.bot.send_message(
                    purchase.user.telegram_id,
                    "✅ <b>خرید شما با موفقیت تایید شد!</b>\n"
                    "🔄 کانفیگ در بخش 'سرویس‌های من' نیز قابل مشاهده است.",
                    reply_markup=get_back_keyboard("my_services"),
                    parse_mode="HTML"
                )
                
                logger.info(f"Config sent to user {purchase.user.telegram_id}")
                
            except Exception as e:
                logger.error(f"Error sending config to user: {e}")
                await callback.message.answer(
                    f"⚠️ خرید تایید شد اما ارسال کانفیگ به کاربر با خطا مواجه شد.\n"
                    f"لطفاً کانفیگ را به صورت دستی برای کاربر ارسال کنید.\n"
                    f"شناسه کاربر: {purchase.user.telegram_id}",
                    reply_markup=get_back_keyboard("admin_purchases")
                )
            
            # Send to sales channel if configured
            result = await session.execute(
                select(SalesChannel).where(SalesChannel.is_active == True)
            )
            sales_channel = result.scalar_one_or_none()
            
            if sales_channel:
                try:
                    channel_text = f"🛒 <b>فروش جدید!</b>\n\n"
                    channel_text += f"👤 کاربر: {purchase.user.first_name or 'نامشخص'}\n"
                    channel_text += f"🆔 شناسه: <code>{purchase.user.telegram_id}</code>\n"
                    channel_text += f"📋 تعرفه: {purchase.plan.name}\n"
                    channel_text += f"💰 مبلغ: {format_price(purchase.amount)} تومان\n"
                    channel_text += f"📅 تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M')}\n"
                    channel_text += f"🔐 کانفیگ: {config_obj.name}"
                    
                    await callback.bot.send_message(
                        sales_channel.channel_id,
                        channel_text,
                        parse_mode="HTML"
                    )
                except Exception as e:
                    logger.error(f"Error sending to sales channel: {e}")
            
            # Send success message to admin
            await callback.message.answer(
                f"✅ خرید #{purchase_id} با موفقیت تایید شد!\n\n"
                f"👤 کاربر: {purchase.user.first_name or 'نامشخص'}\n"
                f"📋 تعرفه: {purchase.plan.name}\n"
                f"💰 مبلغ: {format_price(purchase.amount)} تومان\n"
                f"📅 تاریخ انقضا: {expiry_date.strftime('%Y-%m-%d %H:%M')}\n\n"
                f"🔐 کانفیگ '{config_obj.name}' به کاربر ارسال شد.",
                reply_markup=get_back_keyboard("admin_purchases")
            )
            await callback.answer("✅ خرید با موفقیت تایید شد!")
            
    except Exception as e:
        logger.error(f"Error in approve_purchase: {e}")
        logger.error(traceback.format_exc())
        await callback.message.answer(
            "❌ خطا در تایید خرید.\n"
            "لطفاً دوباره تلاش کنید.",
            reply_markup=get_back_keyboard("admin_purchases")
        )
        await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in approve_purchase: {e}")
        logger.error(traceback.format_exc())
        await callback.message.answer(
            "❌ خطا در تایید خرید.\n"
            "لطفاً دوباره تلاش کنید.",
            reply_markup=get_back_keyboard("admin_purchases")
        )
        await callback.answer()

@router.callback_query(F.data.startswith("reject_purchase_"))
async def reject_purchase(callback: CallbackQuery, state: FSMContext):
    """Start purchase rejection process"""
    try:
        purchase_id = int(callback.data.split("_")[2])
        await state.update_data(purchase_id=purchase_id)
        
        # Send new message instead of editing
        await callback.message.answer(
            "❌ لطفاً دلیل رد خرید را وارد کنید:",
            reply_markup=get_cancel_keyboard()
        )
        await state.set_state(PurchaseStates.waiting_for_rejection_reason)
        await callback.answer()
    except Exception as e:
        logger.error(f"Error in reject_purchase: {e}")
        await callback.message.answer(
            "❌ خطا در شروع فرآیند رد.",
            reply_markup=get_back_keyboard("admin_purchases")
        )
        await callback.answer()

@router.message(PurchaseStates.waiting_for_rejection_reason, F.text)
async def handle_rejection_reason(message: Message, state: FSMContext):
    """Handle rejection reason"""
    try:
        data = await state.get_data()
        purchase_id = data.get('purchase_id')
        reason = message.text
        
        async with AsyncSessionLocal() as session:
            purchase = await session.get(Purchase, purchase_id)
            
            if not purchase:
                await message.answer(
                    "❌ خرید یافت نشد.",
                    reply_markup=get_back_keyboard()
                )
                await state.clear()
                return
            
            purchase.status = PurchaseStatus.REJECTED
            purchase.rejection_reason = reason
            await session.commit()
            
            # Notify user
            try:
                await message.bot.send_message(
                    purchase.user.telegram_id,
                    f"❌ <b>درخواست خرید شما رد شد</b>\n\n"
                    f"📋 دلیل رد:\n{reason}\n\n"
                    f"🔄 برای خرید مجدد، به بخش 'خرید سرویس' مراجعه کنید.",
                    reply_markup=get_back_keyboard(),
                    parse_mode="HTML"
                )
            except Exception as e:
                logger.error(f"Error notifying user about rejection: {e}")
            
            await message.answer(
                f"✅ خرید #{purchase_id} با موفقیت رد شد.\n\n"
                f"📋 دلیل: {reason}\n"
                f"👤 کاربر: {purchase.user.first_name or 'نامشخص'}",
                reply_markup=get_back_keyboard("admin_purchases")
            )
            
            await state.clear()
            
    except Exception as e:
        logger.error(f"Error in handle_rejection_reason: {e}")
        await message.answer(
            "❌ خطا در رد خرید.",
            reply_markup=get_back_keyboard()
        )
        await state.clear()

@router.callback_query(F.data.startswith("service_detail_"))
async def show_service_detail(callback: CallbackQuery):
    """Show service detail"""
    try:
        purchase_id = int(callback.data.split("_")[2])
        
        async with AsyncSessionLocal() as session:
            purchase = await session.get(Purchase, purchase_id)
            
            if not purchase:
                await callback.answer("❌ سرویس یافت نشد.")
                return
            
            # Check if user owns this purchase
            result = await session.execute(
                select(User).where(User.telegram_id == callback.from_user.id)
            )
            user = result.scalar_one_or_none()
            
            if not user or purchase.user_id != user.id:
                await callback.answer("❌ شما به این سرویس دسترسی ندارید.")
                return
            
            status_emoji = {
                PurchaseStatus.PENDING: "⏳ در انتظار تایید",
                PurchaseStatus.APPROVED: "✅ فعال",
                PurchaseStatus.REJECTED: "❌ رد شده",
                PurchaseStatus.EXPIRED: "⏰ منقضی"
            }.get(purchase.status, "❓ نامشخص")
            
            text = f"📋 <b>جزئیات سرویس</b>\n\n"
            text += f"📛 نام: {purchase.plan.name}\n"
            text += f"📅 تاریخ خرید: {purchase.purchase_date.strftime('%Y-%m-%d %H:%M')}\n"
            
            if purchase.expiry_date:
                text += f"📅 تاریخ انقضا: {purchase.expiry_date.strftime('%Y-%m-%d %H:%M')}\n"
            
            text += f"📊 وضعیت: {status_emoji}\n"
            text += f"💰 مبلغ: {format_price(purchase.amount)} تومان\n"
            
            if purchase.status == PurchaseStatus.REJECTED and purchase.rejection_reason:
                text += f"\n❌ دلیل رد: {purchase.rejection_reason}\n"
            
            if purchase.config and purchase.status == PurchaseStatus.APPROVED:
                text += f"\n🔐 کانفیگ:\n<code>{purchase.config.address}</code>\n"
                has_config = True
            else:
                has_config = False
            
            from keyboards.keyboards import get_service_detail_keyboard
            await callback.message.edit_text(
                text,
                reply_markup=get_service_detail_keyboard(purchase_id, has_config),
                parse_mode="HTML"
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in show_service_detail: {e}")
        await callback.message.edit_text(
            "❌ خطا در دریافت جزئیات سرویس.",
            reply_markup=get_back_keyboard("my_services")
        )
        await callback.answer()

@router.callback_query(F.data.startswith("copy_config_"))
async def copy_config(callback: CallbackQuery):
    """Copy config (send again)"""
    try:
        purchase_id = int(callback.data.split("_")[2])
        
        async with AsyncSessionLocal() as session:
            purchase = await session.get(Purchase, purchase_id)
            
            if not purchase or not purchase.config or purchase.status != PurchaseStatus.APPROVED:
                await callback.answer("❌ کانفیگ موجود نیست یا سرویس فعال نیست.")
                return
            
            config_text = f"🔐 <b>کانفیگ V2Ray</b>\n\n"
            config_text += f"📛 نام: {purchase.config.name}\n"
            config_text += f"📋 تعرفه: {purchase.plan.name}\n"
            config_text += f"📅 تاریخ انقضا: {purchase.expiry_date.strftime('%Y-%m-%d %H:%M')}\n\n"
            config_text += f"<code>{purchase.config.address}</code>\n\n"
            config_text += "🔗 برای کپی کردن کانفیگ، روی متن بالا کلیک کنید."
            
            await callback.message.edit_text(
                config_text,
                reply_markup=get_back_keyboard("my_services"),
                parse_mode="HTML"
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in copy_config: {e}")
        await callback.answer("❌ خطا در نمایش کانفیگ.")

@router.callback_query(F.data.startswith("renew_service_"))
async def renew_service(callback: CallbackQuery):
    """Start service renewal process"""
    try:
        purchase_id = int(callback.data.split("_")[2])
        
        async with AsyncSessionLocal() as session:
            purchase = await session.get(Purchase, purchase_id)
            
            if not purchase:
                await callback.answer("❌ سرویس یافت نشد.")
                return
            
            # Get available plans for renewal
            result = await session.execute(
                select(Plan).where(Plan.is_active == True)
            )
            plans = result.scalars().all()
            
            if not plans:
                await callback.answer("❌ هیچ تعرفه‌ای برای تمدید موجود نیست.")
                return
            
            text = f"🔄 <b>تمدید سرویس</b>\n\n"
            text += f"📛 سرویس فعلی: {purchase.plan.name}\n"
            text += f"📅 تاریخ انقضا: {purchase.expiry_date.strftime('%Y-%m-%d %H:%M') if purchase.expiry_date else 'نامشخص'}\n\n"
            text += "📋 لطفاً تعرفه جدید را انتخاب کنید:"
            
            from keyboards.keyboards import get_plans_keyboard
            await callback.message.edit_text(
                text,
                reply_markup=get_plans_keyboard(plans),
                parse_mode="HTML"
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in renew_service: {e}")
        await callback.answer("❌ خطا در شروع فرآیند تمدید.")

@router.callback_query(F.data == "cancel_action")
async def cancel_action(callback: CallbackQuery, state: FSMContext):
    """Cancel current action"""
    await state.clear()
    await callback.message.edit_text(
        "❌ عملیات لغو شد.",
        reply_markup=get_back_keyboard()
    )
    await callback.answer()