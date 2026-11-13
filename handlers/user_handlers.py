from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from sqlalchemy import select, func
from datetime import datetime
import logging
import random

from keyboards.keyboards import (
    get_main_menu_keyboard,
    get_admin_menu_keyboard,
    get_plans_keyboard,
    get_my_services_keyboard,
    get_tickets_keyboard,
    get_guide_keyboard,
    get_back_keyboard,
    get_join_channel_keyboard
)
from database.database import AsyncSessionLocal
from models.models import User, Purchase, Ticket, Setting, Plan, RequiredChannel, TestConfig, UserTestConfig
from config import config

router = Router()
logger = logging.getLogger(__name__)

def format_price(price):
    """Format price with commas and remove decimal zeros"""
    try:
        price_float = float(price)
        if price_float.is_integer():
            return f"{int(price_float):,}"
        else:
            return f"{price_float:,.2f}"
    except:
        return str(price)

@router.message(CommandStart())
async def start_command(message: Message, state: FSMContext):
    """Handle /start command"""
    await state.clear()
    
    try:
        async with AsyncSessionLocal() as session:
            # Check if user exists
            result = await session.execute(
                select(User).where(User.telegram_id == message.from_user.id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                # Create new user
                user = User(
                    telegram_id=message.from_user.id,
                    username=message.from_user.username,
                    first_name=message.from_user.first_name,
                    last_name=message.from_user.last_name
                )
                session.add(user)
                await session.commit()
            
            # Get welcome text from settings
            result = await session.execute(
                select(Setting).where(Setting.key == 'welcome_text')
            )
            welcome_setting = result.scalar_one_or_none()
            welcome_text = welcome_setting.value if welcome_setting else config.DEFAULT_WELCOME_TEXT
            
            # Check if user is admin
            is_admin = message.from_user.id in config.ADMIN_IDS
            
            keyboard = get_admin_menu_keyboard() if is_admin else get_main_menu_keyboard()
            
            await message.answer(
                f"👋 {welcome_text}\n\n"
                f"🆔 شناسه شما: {message.from_user.id}\n"
                f"👤 نام: {message.from_user.first_name or 'نامشخص'}\n\n"
                f"🧪 برای دریافت کانفیگ تستی، روی دکمه 'تست کانفیگ' کلیک کنید.",
                reply_markup=keyboard
            )
            
    except Exception as e:
        logger.error(f"Error in start_command: {e}")
        await message.answer(
            "❌ خطا در اجرای عملیات. لطفاً دوباره تلاش کنید.",
            reply_markup=get_main_menu_keyboard()
        )

@router.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    """Handle back to main menu"""
    await state.clear()
    
    is_admin = callback.from_user.id in config.ADMIN_IDS
    keyboard = get_admin_menu_keyboard() if is_admin else get_main_menu_keyboard()
    
    try:
        await callback.message.edit_text(
            "🏠 منوی اصلی:",
            reply_markup=keyboard
        )
    except Exception:
        await callback.message.answer(
            "🏠 منوی اصلی:",
            reply_markup=keyboard
        )
    await callback.answer()

@router.callback_query(F.data == "plans")
async def show_plans(callback: CallbackQuery):
    """Show available plans - This is the purchase page"""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Plan).where(Plan.is_active == True)
            )
            plans = result.scalars().all()
            
            if not plans:
                await callback.message.edit_text(
                    "❌ هیچ تعرفه‌ای در حال حاضر موجود نیست.",
                    reply_markup=get_back_keyboard()
                )
                await callback.answer()
                return
            
            text = "🛒 <b>خرید سرویس</b>\n\n"
            text += "📊 تعرفه‌های موجود:\n\n"
            for plan in plans:
                text += f"🔹 {plan.name}\n"
                text += f"   💾 حجم: {plan.volume}\n"
                text += f"   ⏰ مدت: {plan.duration}\n"
                text += f"   💰 قیمت: {format_price(plan.price)} تومان\n"
                text += f"   📝 {plan.description or 'بدون توضیحات'}\n\n"
            
            from keyboards.keyboards import get_plans_keyboard
            await callback.message.edit_text(
                text,
                reply_markup=get_plans_keyboard(plans),
                parse_mode="HTML"
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in show_plans: {e}")
        await callback.message.edit_text(
            "❌ خطا در دریافت تعرفه‌ها.",
            reply_markup=get_back_keyboard()
        )
        await callback.answer()

@router.callback_query(F.data == "my_services")
async def show_my_services(callback: CallbackQuery):
    """Show user's services"""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == callback.from_user.id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                await callback.answer("❌ کاربر یافت نشد.")
                return
            
            result = await session.execute(
                select(Purchase)
                .where(Purchase.user_id == user.id)
                .order_by(Purchase.purchase_date.desc())
            )
            purchases = result.scalars().all()
            
            if not purchases:
                await callback.message.edit_text(
                    "📋 شما هیچ سرویسی خریداری نکرده‌اید.",
                    reply_markup=get_back_keyboard()
                )
                await callback.answer()
                return
            
            from keyboards.keyboards import get_my_services_keyboard
            await callback.message.edit_text(
                "📋 سرویس‌های من:",
                reply_markup=get_my_services_keyboard(purchases)
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in show_my_services: {e}")
        await callback.message.edit_text(
            "❌ خطا در دریافت سرویس‌ها.",
            reply_markup=get_back_keyboard()
        )
        await callback.answer()

@router.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    """Show user profile"""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(User).where(User.telegram_id == callback.from_user.id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                await callback.answer("❌ کاربر یافت نشد.")
                return
            
            result = await session.execute(
                select(func.count(Purchase.id))
                .where(Purchase.user_id == user.id)
            )
            purchase_count = result.scalar()
            
            # Get test config history
            result = await session.execute(
                select(UserTestConfig)
                .where(UserTestConfig.user_id == user.id)
                .order_by(UserTestConfig.received_at.desc())
            )
            test_configs = result.scalars().all()
            
            text = f"👤 <b>پروفایل کاربری</b>\n\n"
            text += f"🆔 شناسه: {user.telegram_id}\n"
            text += f"👤 نام: {user.first_name or 'نامشخص'}\n"
            text += f"📝 نام کاربری: @{user.username or 'ندارد'}\n"
            text += f"📅 تاریخ عضویت: {user.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            text += f"🛒 تعداد خریدها: {purchase_count}\n"
            if test_configs:
                text += f"🧪 تعداد کانفیگ‌های تستی دریافت شده: {len(test_configs)}\n"
            text += f"📊 وضعیت: {'✅ فعال' if user.status.value == 'active' else '🔴 مسدود'}"
            
            await callback.message.edit_text(
                text,
                reply_markup=get_back_keyboard(),
                parse_mode="HTML"
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in show_profile: {e}")
        await callback.message.edit_text(
            "❌ خطا در دریافت اطلاعات کاربری.",
            reply_markup=get_back_keyboard()
        )
        await callback.answer()

@router.callback_query(F.data == "guide")
async def show_guide(callback: CallbackQuery):
    """Show guide menu"""
    try:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Setting).where(Setting.key == 'guide_text')
            )
            guide_setting = result.scalar_one_or_none()
            
            text = "📖 <b>راهنمای اتصال</b>\n\n"
            if guide_setting:
                text += guide_setting.value
            else:
                text += "راهنمای اتصال به سرویس‌های V2Ray:\n\n"
                text += "1️⃣ دانلود برنامه مناسب برای دستگاه خود\n"
                text += "2️⃣ دریافت کانفیگ از بخش 'سرویس‌های من'\n"
                text += "3️⃣ وارد کردن کانفیگ در برنامه\n"
                text += "4️⃣ اتصال و استفاده\n\n"
                text += "برای اطلاعات بیشتر، روی گزینه مربوطه کلیک کنید."
            
            await callback.message.edit_text(
                text,
                reply_markup=get_guide_keyboard(),
                parse_mode="HTML"
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in show_guide: {e}")
        await callback.message.edit_text(
            "❌ خطا در دریافت راهنما.",
            reply_markup=get_back_keyboard()
        )
        await callback.answer()

@router.callback_query(F.data == "get_test_config")
async def get_test_config(callback: CallbackQuery):
    """Get a test config for user"""
    try:
        async with AsyncSessionLocal() as session:
            # Check if user exists
            result = await session.execute(
                select(User).where(User.telegram_id == callback.from_user.id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                await callback.answer("❌ کاربر یافت نشد.")
                return
            
            # Check if user already got a test config
            result = await session.execute(
                select(UserTestConfig)
                .where(UserTestConfig.user_id == user.id)
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                # User already got a test config
                await callback.message.edit_text(
                    "🧪 <b>شما قبلاً یک کانفیگ تستی دریافت کرده‌اید!</b>\n\n"
                    "هر کاربر فقط <b>یکبار</b> می‌تواند کانفیگ تستی دریافت کند.\n\n"
                    "🛒 برای خرید سرویس اصلی، به بخش 'خرید سرویس' مراجعه کنید.",
                    reply_markup=get_back_keyboard(),
                    parse_mode="HTML"
                )
                await callback.answer()
                return
            
            # Get an available test config (random)
            result = await session.execute(
                select(TestConfig)
                .where(TestConfig.is_active == True)
                .where(TestConfig.is_used == False)
            )
            test_configs = result.scalars().all()
            
            # Select random config if available
            test_config = None
            if test_configs:
                test_config = random.choice(test_configs)
            
            if test_config:
                # Mark as used
                test_config.is_used = True
                test_config.used_by_user_id = user.id
                test_config.used_at = datetime.now()
                
                # Save to history
                user_test_config = UserTestConfig(
                    user_id=user.id,
                    test_config_id=test_config.id
                )
                session.add(user_test_config)
                await session.commit()
                
                # Send test config to user
                config_text = f"🧪 <b>کانفیگ تستی اختصاصی شما</b>\n\n"
                config_text += f"📛 نام: {test_config.name}\n"
                config_text += f"🆔 شناسه: #{test_config.id}\n\n"
                config_text += f"<code>{test_config.address}</code>\n\n"
                config_text += "🔗 برای کپی کردن، روی متن بالا کلیک کنید.\n"
                config_text += "📱 لینک‌ها را در برنامه مربوطه وارد کنید.\n\n"
                config_text += "⚠️ این کانفیگ فقط <b>یکبار</b> قابل استفاده است و منحصر به فرد می‌باشد."
                
                await callback.message.edit_text(
                    f"🧪 <b>کانفیگ تستی شما</b>\n\n"
                    f"{config_text}",
                    reply_markup=get_back_keyboard(),
                    parse_mode="HTML"
                )
                await callback.answer("✅ کانفیگ تستی با موفقیت ارسال شد!")
            else:
                await callback.message.edit_text(
                    "❌ متأسفانه در حال حاضر هیچ کانفیگ تستی موجود نیست.\n\n"
                    "🛒 می‌توانید از بخش 'خرید سرویس' اقدام به خرید کنید.",
                    reply_markup=get_back_keyboard(),
                    parse_mode="HTML"
                )
                await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in get_test_config: {e}")
        await callback.message.edit_text(
            "❌ خطا در دریافت کانفیگ تستی.",
            reply_markup=get_back_keyboard()
        )
        await callback.answer()

@router.callback_query(F.data.startswith("guide_"))
async def show_guide_detail(callback: CallbackQuery):
    """Show detailed guide for specific platform"""
    platform = callback.data.split("_")[1]
    
    guides = {
        "android": "📱 <b>راهنمای اتصال در Android</b>\n\n"
                   "1. دانلود برنامه V2RayNG از Google Play\n"
                   "2. وارد کردن کانفیگ از بخش 'سرویس‌های من'\n"
                   "3. فعال کردن اتصال\n\n"
                   "نکته: برای اطلاعات بیشتر به ویدئوهای آموزشی مراجعه کنید.",
        
        "iphone": "📱 <b>راهنمای اتصال در iPhone</b>\n\n"
                  "1. دانلود برنامه Shadowrocket از App Store\n"
                  "2. وارد کردن کانفیگ از بخش 'سرویس‌های من'\n"
                  "3. فعال کردن اتصال\n\n"
                  "نکته: برای اطلاعات بیشتر به ویدئوهای آموزشی مراجعه کنید.",
        
        "windows": "💻 <b>راهنمای اتصال در Windows</b>\n\n"
                   "1. دانلود برنامه V2RayN از GitHub\n"
                   "2. وارد کردن کانفیگ از بخش 'سرویس‌های من'\n"
                   "3. فعال کردن اتصال\n\n"
                   "نکته: برای اطلاعات بیشتر به ویدئوهای آموزشی مراجعه کنید.",
        
        "macos": "💻 <b>راهنمای اتصال در MacOS</b>\n\n"
                 "1. دانلود برنامه V2RayX از GitHub\n"
                 "2. وارد کردن کانفیگ از بخش 'سرویس‌های من'\n"
                 "3. فعال کردن اتصال\n\n"
                 "نکته: برای اطلاعات بیشتر به ویدئوهای آموزشی مراجعه کنید.",
        
        "full": "📖 <b>راهنمای کامل اتصال</b>\n\n"
                "مراحل کلی:\n"
                "1️⃣ انتخاب تعرفه مناسب از بخش 'تعرفه‌ها'\n"
                "2️⃣ خرید سرویس از بخش 'خرید سرویس'\n"
                "3️⃣ پرداخت مبلغ از طریق کارت بانکی\n"
                "4️⃣ دریافت کانفیگ از بخش 'سرویس‌های من'\n"
                "5️⃣ نصب و راه‌اندازی برنامه مناسب دستگاه خود\n"
                "6️⃣ وارد کردن کانفیگ و اتصال\n\n"
                "⚠️ نکات مهم:\n"
                "- کانفیگ‌ها به صورت اختصاصی برای هر کاربر تولید می‌شوند\n"
                "- در صورت بروز مشکل، از بخش پشتیبانی استفاده کنید"
    }
    
    guide_text = guides.get(platform, "راهنمای مورد نظر یافت نشد.")
    
    await callback.message.edit_text(
        guide_text,
        reply_markup=get_back_keyboard("guide"),
        parse_mode="HTML"
    )
    await callback.answer()

@router.callback_query(F.data == "check_membership")
async def check_membership(callback: CallbackQuery):
    """Check membership again"""
    is_admin = callback.from_user.id in config.ADMIN_IDS
    keyboard = get_admin_menu_keyboard() if is_admin else get_main_menu_keyboard()
    
    try:
        # Get required channels
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(RequiredChannel).where(RequiredChannel.is_active == True)
            )
            required_channels = result.scalars().all()
            
            if not required_channels:
                await callback.message.edit_text(
                    "✅ هیچ کانال اجباری وجود ندارد.\n\n"
                    "🏠 منوی اصلی:",
                    reply_markup=keyboard
                )
                await callback.answer()
                return
            
            # Check membership
            not_member = []
            for channel in required_channels:
                try:
                    chat_id = channel.channel_id
                    if channel.channel_username and channel.channel_username.startswith('@'):
                        try:
                            chat = await callback.bot.get_chat(channel.channel_username)
                            chat_id = str(chat.id)
                        except:
                            chat_id = channel.channel_id
                    
                    member = await callback.bot.get_chat_member(chat_id, callback.from_user.id)
                    if member.status in ['left', 'kicked']:
                        not_member.append(channel)
                except Exception as e:
                    logger.error(f"Error checking channel {channel.channel_id}: {e}")
                    not_member.append(channel)
            
            if not_member:
                text = "🔒 <b>دسترسی محدود</b>\n\n"
                text += "شما هنوز در کانال‌های زیر عضو نشده‌اید:\n\n"
                for channel in not_member:
                    display_name = channel.channel_title or channel.channel_id
                    text += f"📢 {display_name}\n"
                    if channel.channel_username:
                        text += f"   @{channel.channel_username.replace('@', '')}\n"
                    text += "\n"
                text += "✅ پس از عضویت، دوباره روی <b>'بررسی مجدد'</b> کلیک کنید."
                
                first_channel = not_member[0]
                channel_username = first_channel.channel_username if first_channel.channel_username else None
                await callback.message.edit_text(
                    text,
                    reply_markup=get_join_channel_keyboard(channel_username),
                    parse_mode="HTML"
                )
                await callback.answer()
            else:
                await callback.message.edit_text(
                    "✅ عضویت شما در تمام کانال‌ها تایید شد!\n\n"
                    "🏠 منوی اصلی:",
                    reply_markup=keyboard
                )
                await callback.answer("✅ عضویت شما تایید شد!")
                
    except Exception as e:
        logger.error(f"Error in check_membership: {e}")
        await callback.message.edit_text(
            "❌ خطا در بررسی عضویت. لطفاً دوباره تلاش کنید.",
            reply_markup=get_back_keyboard()
        )
        await callback.answer()

@router.callback_query(F.data == "support")
async def show_support(callback: CallbackQuery):
    """Show support menu"""
    try:
        async with AsyncSessionLocal() as session:
            # Get user
            result = await session.execute(
                select(User).where(User.telegram_id == callback.from_user.id)
            )
            user = result.scalar_one_or_none()
            
            if not user:
                await callback.answer("❌ کاربر یافت نشد.")
                return
            
            result = await session.execute(
                select(Ticket)
                .where(Ticket.user_id == user.id)
                .order_by(Ticket.created_at.desc())
            )
            tickets = result.scalars().all()
            
            if tickets:
                text = "💬 <b>تیکت‌های پشتیبانی</b>\n\n"
                for ticket in tickets:
                    status_emoji = "🔴" if ticket.status.value == "open" else "🟢"
                    text += f"{status_emoji} #{ticket.id}: {ticket.subject[:30]}\n"
                    text += f"   {ticket.created_at.strftime('%Y-%m-%d %H:%M')}\n\n"
            else:
                text = "🎧 برای ارتباط با پشتیبانی و ثبت تیکت، به آیدی زیر پیام دهید:\n\n👤 @di_izirvpn\n\n⚡ کارشناسان ما در سریع‌ترین زمان ممکن پاسخگوی شما خواهند بود."
            
            await callback.message.edit_text(
                text,
                reply_markup=get_back_keyboard(),
                parse_mode="HTML"
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in show_support: {e}")
        await callback.message.edit_text(
            "❌ خطا در دریافت تیکت‌ها.",
            reply_markup=get_back_keyboard()
        )
        await callback.answer()