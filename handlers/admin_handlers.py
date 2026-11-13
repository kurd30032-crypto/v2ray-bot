from aiogram import Router, F, types
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from datetime import datetime, timedelta
from sqlalchemy import func, select
import logging
import os

from keyboards.keyboards import (
    get_admin_menu_keyboard,
    get_admin_users_keyboard,
    get_user_detail_keyboard,
    get_back_keyboard,
    get_cancel_keyboard,
    get_confirmation_keyboard,
    get_test_configs_admin_keyboard,
    get_test_config_edit_keyboard
)
from database.database import AsyncSessionLocal
from config import config
from database.database import AsyncSessionLocal
from models.models import User, Purchase, Plan, Config, BankCard, Ticket, TestConfig, UserTestConfig

class TestConfigStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_address = State()
    waiting_for_edit_name = State()
    waiting_for_edit_address = State()
    
router = Router()
logger = logging.getLogger(__name__)

class BroadcastStates(StatesGroup):
    waiting_for_broadcast_text = State()
    waiting_for_broadcast_photo = State()
    waiting_for_broadcast_video = State()
    waiting_for_broadcast_file = State()
    waiting_for_message_to_user = State()

# Admin filter
def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS

@router.message(F.text == "/admin")
async def admin_panel(message: Message):
    """Show admin panel"""
    if not is_admin(message.from_user.id):
        await message.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    await message.answer(
        "🔐 پنل مدیریت:\n\n"
        "از منوی زیر برای مدیریت ربات استفاده کنید.",
        reply_markup=get_admin_menu_keyboard()
    )

@router.callback_query(F.data == "admin_panel")
async def admin_panel_callback(callback: CallbackQuery):
    """Show admin panel from callback"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    await callback.message.edit_text(
        "🔐 پنل مدیریت:\n\n"
        "از منوی زیر برای مدیریت ربات استفاده کنید.",
        reply_markup=get_admin_menu_keyboard()
    )
    await callback.answer()

@router.callback_query(F.data == "admin_dashboard")
async def admin_dashboard(callback: CallbackQuery):
    """Show admin dashboard"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    try:
        async with AsyncSessionLocal() as session:
            # Total users
            total_users = await session.execute(
                select(func.count(User.id))
            )
            total_users = total_users.scalar()
            
            # Total purchases
            total_purchases = await session.execute(
                select(func.count(Purchase.id))
            )
            total_purchases = total_purchases.scalar()
            
            # Today's sales
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            today_sales = await session.execute(
                select(func.sum(Purchase.amount))
                .where(Purchase.purchase_date >= today_start)
                .where(Purchase.status == "approved")
            )
            today_sales = today_sales.scalar() or 0
            
            # Total revenue
            total_revenue = await session.execute(
                select(func.sum(Purchase.amount))
                .where(Purchase.status == "approved")
            )
            total_revenue = total_revenue.scalar() or 0
            
            # Active services
            active_services = await session.execute(
                select(func.count(Purchase.id))
                .where(Purchase.status == "approved")
                .where(Purchase.expiry_date > datetime.now())
            )
            active_services = active_services.scalar()
            
            # Pending purchases
            pending_purchases = await session.execute(
                select(func.count(Purchase.id))
                .where(Purchase.status == "pending")
            )
            pending_purchases = pending_purchases.scalar()
            
            text = f"📊 داشبورد مدیریت:\n\n"
            text += f"👥 تعداد کاربران: {total_users:,}\n"
            text += f"🛒 تعداد خریدها: {total_purchases:,}\n"
            text += f"💰 فروش امروز: {today_sales:,} تومان\n"
            text += f"💵 مجموع فروش: {total_revenue:,} تومان\n"
            text += f"✅ سرویس‌های فعال: {active_services:,}\n"
            text += f"⏳ درخواست‌های در انتظار: {pending_purchases:,}"
            
            await callback.message.edit_text(
                text,
                reply_markup=get_back_keyboard("admin_panel")
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in admin_dashboard: {e}")
        await callback.message.edit_text(
            "❌ خطا در دریافت اطلاعات داشبورد.",
            reply_markup=get_back_keyboard("admin_panel")
        )
        await callback.answer()

@router.callback_query(F.data == "admin_users")
async def admin_users(callback: CallbackQuery):
    """Show users list"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    try:
        async with AsyncSessionLocal() as session:
            users = await session.execute(
                select(User).order_by(User.created_at.desc()).limit(20)
            )
            users = users.scalars().all()
            
            if not users:
                await callback.message.edit_text(
                    "👥 هیچ کاربری یافت نشد.",
                    reply_markup=get_back_keyboard("admin_panel")
                )
                await callback.answer()
                return
            
            await callback.message.edit_text(
                "👥 لیست کاربران (۲۰ نفر اخیر):\n\n"
                "برای مشاهده جزئیات کاربر، روی نام او کلیک کنید.",
                reply_markup=get_admin_users_keyboard(users)
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in admin_users: {e}")
        await callback.message.edit_text(
            "❌ خطا در دریافت لیست کاربران.",
            reply_markup=get_back_keyboard("admin_panel")
        )
        await callback.answer()

@router.callback_query(F.data.startswith("admin_user_"))
async def admin_user_detail(callback: CallbackQuery):
    """Show user detail"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    user_id = int(callback.data.split("_")[2])
    
    try:
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            
            if not user:
                await callback.answer("❌ کاربر یافت نشد.")
                return
            
            # Get user purchases
            purchases = await session.execute(
                select(Purchase).where(Purchase.user_id == user.id)
            )
            purchases = purchases.scalars().all()
            
            text = f"👤 اطلاعات کاربر:\n\n"
            text += f"🆔 شناسه: {user.telegram_id}\n"
            text += f"👤 نام: {user.first_name or 'نامشخص'}\n"
            text += f"📝 نام کاربری: @{user.username or 'ندارد'}\n"
            text += f"📅 تاریخ عضویت: {user.created_at.strftime('%Y-%m-%d %H:%M')}\n"
            text += f"📊 وضعیت: {'✅ فعال' if user.status.value == 'active' else '🔴 مسدود'}\n"
            text += f"🛒 تعداد خریدها: {len(purchases)}\n\n"
            
            if purchases:
                text += "📋 آخرین خریدها:\n"
                for purchase in purchases[:5]:
                    status_emoji = {
                        "pending": "⏳",
                        "approved": "✅",
                        "rejected": "❌",
                        "expired": "⏰"
                    }.get(purchase.status.value, "❓")
                    text += f"{status_emoji} {purchase.plan.name} - {purchase.amount:,} تومان\n"
            
            await callback.message.edit_text(
                text,
                reply_markup=get_user_detail_keyboard(user.id)
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in admin_user_detail: {e}")
        await callback.answer("❌ خطا در دریافت اطلاعات کاربر.")

@router.callback_query(F.data.startswith("block_user_"))
async def block_user(callback: CallbackQuery):
    """Block user"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    user_id = int(callback.data.split("_")[2])
    
    try:
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            
            if not user:
                await callback.answer("❌ کاربر یافت نشد.")
                return
            
            user.status = "blocked"
            await session.commit()
            
            await callback.message.edit_text(
                f"✅ کاربر {user.first_name or user.username or user.telegram_id} با موفقیت مسدود شد.",
                reply_markup=get_back_keyboard("admin_users")
            )
            
            # Notify user
            try:
                await callback.bot.send_message(
                    user.telegram_id,
                    "🔴 حساب کاربری شما توسط ادمین مسدود شده است.\n"
                    "برای اطلاعات بیشتر با پشتیبانی تماس بگیرید."
                )
            except Exception as e:
                logger.error(f"Error notifying blocked user: {e}")
            
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in block_user: {e}")
        await callback.answer("❌ خطا در مسدودسازی کاربر.")

@router.callback_query(F.data.startswith("unblock_user_"))
async def unblock_user(callback: CallbackQuery):
    """Unblock user"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    user_id = int(callback.data.split("_")[2])
    
    try:
        async with AsyncSessionLocal() as session:
            user = await session.get(User, user_id)
            
            if not user:
                await callback.answer("❌ کاربر یافت نشد.")
                return
            
            user.status = "active"
            await session.commit()
            
            await callback.message.edit_text(
                f"✅ کاربر {user.first_name or user.username or user.telegram_id} با موفقیت رفع مسدود شد.",
                reply_markup=get_back_keyboard("admin_users")
            )
            
            # Notify user
            try:
                await callback.bot.send_message(
                    user.telegram_id,
                    "🟢 حساب کاربری شما توسط ادمین رفع مسدود شد.\n"
                    "اکنون می‌توانید از خدمات ربات استفاده کنید."
                )
            except Exception as e:
                logger.error(f"Error notifying unblocked user: {e}")
            
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in unblock_user: {e}")
        await callback.answer("❌ خطا در رفع مسدودسازی کاربر.")

@router.callback_query(F.data == "admin_broadcast")
async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
    """Start broadcast process"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    await callback.message.edit_text(
        "📨 ارسال پیام همگانی:\n\n"
        "لطفاً متن پیام را ارسال کنید.\n"
        "پس از ارسال، می‌توانید عکس، ویدئو یا فایل نیز اضافه کنید.",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(BroadcastStates.waiting_for_broadcast_text)
    await callback.answer()

@router.message(BroadcastStates.waiting_for_broadcast_text, F.text)
async def handle_broadcast_text(message: Message, state: FSMContext):
    """Handle broadcast text"""
    await state.update_data(broadcast_text=message.text)
    await state.update_data(broadcast_type="text")
    
    # Check if user wants to add media
    await message.answer(
        "📨 متن پیام ثبت شد.\n\n"
        "✅ برای ارسال فقط متن، روی دکمه زیر کلیک کنید.\n"
        "📸 برای ارسال عکس، عکس را ارسال کنید.\n"
        "🎬 برای ارسال ویدئو، ویدئو را ارسال کنید.\n"
        "📁 برای ارسال فایل، فایل را ارسال کنید.",
        reply_markup=get_confirmation_keyboard("broadcast", "text")
    )

@router.message(BroadcastStates.waiting_for_broadcast_text, F.photo)
async def handle_broadcast_photo(message: Message, state: FSMContext):
    """Handle broadcast photo"""
    photo = message.photo[-1]
    await state.update_data(broadcast_photo=photo.file_id)
    
    if await state.get_data():
        data = await state.get_data()
        if data.get('broadcast_text'):
            await message.answer(
                "📸 عکس ثبت شد.\n\n"
                "✅ برای ارسال، روی دکمه زیر کلیک کنید.",
                reply_markup=get_confirmation_keyboard("broadcast", "photo")
            )
        else:
            await message.answer(
                "📸 عکس ثبت شد.\n\n"
                "📝 لطفاً متن پیام را نیز ارسال کنید.",
                reply_markup=get_cancel_keyboard()
            )

@router.callback_query(F.data.startswith("confirm_broadcast_"))
async def confirm_broadcast(callback: CallbackQuery, state: FSMContext):
    """Confirm and send broadcast"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    broadcast_type = callback.data.split("_")[2]
    data = await state.get_data()
    
    try:
        async with AsyncSessionLocal() as session:
            users = await session.execute(
                select(User).where(User.status == "active")
            )
            users = users.scalars().all()
            
            if not users:
                await callback.message.edit_text(
                    "❌ هیچ کاربر فعالی برای ارسال وجود ندارد.",
                    reply_markup=get_back_keyboard("admin_panel")
                )
                await callback.answer()
                await state.clear()
                return
            
            sent_count = 0
            failed_count = 0
            
            # Send to each user
            for user in users:
                try:
                    if broadcast_type == "text":
                        await callback.bot.send_message(
                            user.telegram_id,
                            data.get('broadcast_text', '')
                        )
                    elif broadcast_type == "photo":
                        await callback.bot.send_photo(
                            user.telegram_id,
                            data.get('broadcast_photo'),
                            caption=data.get('broadcast_text', '')
                        )
                    # Add more media types as needed
                    
                    sent_count += 1
                except Exception as e:
                    logger.error(f"Error sending broadcast to {user.telegram_id}: {e}")
                    failed_count += 1
            
            await callback.message.edit_text(
                f"✅ پیام همگانی ارسال شد!\n\n"
                f"📤 ارسال شد: {sent_count}\n"
                f"❌ ناموفق: {failed_count}",
                reply_markup=get_back_keyboard("admin_panel")
            )
            await callback.answer()
            await state.clear()
            
    except Exception as e:
        logger.error(f"Error in confirm_broadcast: {e}")
        await callback.message.edit_text(
            "❌ خطا در ارسال پیام همگانی.",
            reply_markup=get_back_keyboard("admin_panel")
        )
        await callback.answer()
        await state.clear()

@router.callback_query(F.data.startswith("send_message_to_user_"))
async def send_message_to_user(callback: CallbackQuery, state: FSMContext):
    """Start direct message to user"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    user_id = int(callback.data.split("_")[4])
    await state.update_data(target_user_id=user_id)
    
    await callback.message.edit_text(
        "💬 ارسال پیام به کاربر:\n\n"
        "لطفاً متن پیام را ارسال کنید.",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(BroadcastStates.waiting_for_message_to_user)
    await callback.answer()

@router.message(BroadcastStates.waiting_for_message_to_user, F.text)
async def handle_message_to_user(message: Message, state: FSMContext):
    """Handle direct message to user"""
    data = await state.get_data()
    target_user_id = data.get('target_user_id')
    text = message.text
    
    try:
        async with AsyncSessionLocal() as session:
            user = await session.get(User, target_user_id)
            
            if not user:
                await message.answer(
                    "❌ کاربر یافت نشد.",
                    reply_markup=get_back_keyboard("admin_users")
                )
                await state.clear()
                return
            
            # Send message to user
            await message.bot.send_message(
                user.telegram_id,
                f"📨 پیام از ادمین:\n\n{text}"
            )
            
            await message.answer(
                f"✅ پیام با موفقیت به کاربر {user.first_name or user.username or user.telegram_id} ارسال شد.",
                reply_markup=get_back_keyboard("admin_users")
            )
            await state.clear()
            
    except Exception as e:
        logger.error(f"Error in handle_message_to_user: {e}")
        await message.answer(
            "❌ خطا در ارسال پیام به کاربر.",
            reply_markup=get_back_keyboard("admin_users")
        )
        await state.clear()
        
        
        
@router.callback_query(F.data == "admin_test_configs")
async def admin_test_configs(callback: CallbackQuery):
    """Show admin test configs management"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    try:
        async with AsyncSessionLocal() as session:
            # Get all test configs
            result = await session.execute(
                select(TestConfig).order_by(TestConfig.created_at.desc())
            )
            configs = result.scalars().all()
            
            # Get stats
            total = len(configs)
            used = len([c for c in configs if c.is_used])
            available = total - used
            
            text = f"🧪 <b>مدیریت کانفیگ‌های تستی</b>\n\n"
            text += f"📊 آمار:\n"
            text += f"   📌 کل کانفیگ‌ها: {total}\n"
            text += f"   ✅ استفاده شده: {used}\n"
            text += f"   🆓 موجود: {available}\n\n"
            text += "کانفیگ‌های تستی برای کاربران جدید ارسال می‌شوند.\n"
            text += "هر کانفیگ فقط یکبار استفاده می‌شود."
            
            await callback.message.edit_text(
                text,
                reply_markup=get_test_configs_admin_keyboard(configs),
                parse_mode="HTML"
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in admin_test_configs: {e}")
        await callback.message.edit_text(
            "❌ خطا در دریافت کانفیگ‌های تستی.",
            reply_markup=get_back_keyboard("admin_panel")
        )
        await callback.answer()

@router.callback_query(F.data == "admin_add_test_config")
async def admin_add_test_config(callback: CallbackQuery, state: FSMContext):
    """Start add test config process"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    await callback.message.edit_text(
        "🧪 <b>افزودن کانفیگ تستی جدید</b>\n\n"
        "📛 لطفاً نام کانفیگ را وارد کنید:",
        reply_markup=get_cancel_keyboard(),
        parse_mode="HTML"
    )
    await state.set_state(TestConfigStates.waiting_for_name)
    await callback.answer()

@router.message(TestConfigStates.waiting_for_name, F.text)
async def handle_test_config_name(message: Message, state: FSMContext):
    """Handle test config name"""
    await state.update_data(name=message.text)
    
    await message.answer(
        "🔗 لطفاً آدرس کانفیگ V2Ray را وارد کنید:\n\n"
        "مثال: vless://... یا vmess://...\n"
        "⚠️ می‌توانید چندین لینک را با Enter جدا کنید.",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(TestConfigStates.waiting_for_address)

@router.message(TestConfigStates.waiting_for_address, F.text)
async def handle_test_config_address(message: Message, state: FSMContext):
    """Handle test config address"""
    await state.update_data(address=message.text)
    
    data = await state.get_data()
    
    try:
        async with AsyncSessionLocal() as session:
            test_config = TestConfig(
                name=data['name'],
                address=data['address']
            )
            session.add(test_config)
            await session.commit()
            
            await message.answer(
                f"✅ کانفیگ تستی '{test_config.name}' با موفقیت ایجاد شد!\n\n"
                f"📛 نام: {test_config.name}\n"
                f"🆔 شناسه: #{test_config.id}\n"
                f"📊 وضعیت: {'🟢 فعال' if test_config.is_active else '🔴 غیرفعال'}\n"
                f"📌 استفاده: {'❌ استفاده نشده' if not test_config.is_used else '✅ استفاده شده'}",
                reply_markup=get_back_keyboard("admin_test_configs")
            )
            await state.clear()
            
    except Exception as e:
        logger.error(f"Error creating test config: {e}")
        await message.answer(
            "❌ خطا در ایجاد کانفیگ تستی.",
            reply_markup=get_back_keyboard("admin_test_configs")
        )
        await state.clear()

@router.callback_query(F.data.startswith("admin_test_config_"))
async def admin_test_config_detail(callback: CallbackQuery):
    """Show test config detail"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    config_id = int(callback.data.split("_")[3])
    
    try:
        async with AsyncSessionLocal() as session:
            test_config = await session.get(TestConfig, config_id)
            
            if not test_config:
                await callback.answer("❌ کانفیگ تستی یافت نشد.")
                return
            
            status_emoji = "🟢" if test_config.is_active else "🔴"
            used_emoji = "✅" if test_config.is_used else "❌"
            
            text = f"🧪 <b>جزئیات کانفیگ تستی</b>\n\n"
            text += f"📛 نام: {test_config.name}\n"
            text += f"🆔 شناسه: #{test_config.id}\n"
            text += f"📊 وضعیت: {status_emoji} {'فعال' if test_config.is_active else 'غیرفعال'}\n"
            text += f"📌 استفاده شده: {used_emoji}\n"
            
            if test_config.is_used and test_config.used_by:
                text += f"👤 استفاده شده توسط: {test_config.used_by.first_name or test_config.used_by.username or test_config.used_by.telegram_id}\n"
                text += f"📅 تاریخ استفاده: {test_config.used_at.strftime('%Y-%m-%d %H:%M')}\n"
            
            text += f"\n🔗 آدرس:\n<code>{test_config.address[:200]}...</code>\n"
            text += f"\n📅 تاریخ ایجاد: {test_config.created_at.strftime('%Y-%m-%d %H:%M')}"
            
            await callback.message.edit_text(
                text,
                reply_markup=get_test_config_edit_keyboard(config_id),
                parse_mode="HTML"
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error in admin_test_config_detail: {e}")
        await callback.answer("❌ خطا در دریافت جزئیات کانفیگ تستی.")

@router.callback_query(F.data.startswith("edit_test_config_"))
async def edit_test_config_start(callback: CallbackQuery, state: FSMContext):
    """Start test config edit process"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    config_id = int(callback.data.split("_")[3])
    await state.update_data(edit_config_id=config_id)
    
    await callback.message.edit_text(
        "✏️ ویرایش کانفیگ تستی:\n\n"
        "📛 نام جدید را وارد کنید (برای حفظ مقدار فعلی، 'همان' را وارد کنید):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(TestConfigStates.waiting_for_edit_name)
    await callback.answer()

@router.message(TestConfigStates.waiting_for_edit_name, F.text)
async def handle_edit_test_config_name(message: Message, state: FSMContext):
    """Handle edit test config name"""
    await state.update_data(edit_name=message.text if message.text != "همان" else None)
    
    await message.answer(
        "🔗 آدرس جدید را وارد کنید (برای حفظ مقدار فعلی، 'همان' را وارد کنید):",
        reply_markup=get_cancel_keyboard()
    )
    await state.set_state(TestConfigStates.waiting_for_edit_address)

@router.message(TestConfigStates.waiting_for_edit_address, F.text)
async def handle_edit_test_config_address(message: Message, state: FSMContext):
    """Handle edit test config address"""
    await state.update_data(edit_address=message.text if message.text != "همان" else None)
    
    data = await state.get_data()
    config_id = data.get('edit_config_id')
    
    try:
        async with AsyncSessionLocal() as session:
            test_config = await session.get(TestConfig, config_id)
            
            if not test_config:
                await message.answer(
                    "❌ کانفیگ تستی یافت نشد.",
                    reply_markup=get_back_keyboard("admin_test_configs")
                )
                await state.clear()
                return
            
            if data.get('edit_name') is not None:
                test_config.name = data['edit_name']
            if data.get('edit_address') is not None:
                test_config.address = data['edit_address']
            
            await session.commit()
            
            await message.answer(
                f"✅ کانفیگ تستی '{test_config.name}' با موفقیت ویرایش شد!",
                reply_markup=get_back_keyboard("admin_test_configs")
            )
            await state.clear()
            
    except Exception as e:
        logger.error(f"Error editing test config: {e}")
        await message.answer(
            "❌ خطا در ویرایش کانفیگ تستی.",
            reply_markup=get_back_keyboard("admin_test_configs")
        )
        await state.clear()

@router.callback_query(F.data.startswith("delete_test_config_"))
async def delete_test_config(callback: CallbackQuery):
    """Delete test config"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    config_id = int(callback.data.split("_")[3])
    
    try:
        async with AsyncSessionLocal() as session:
            test_config = await session.get(TestConfig, config_id)
            
            if not test_config:
                await callback.answer("❌ کانفیگ تستی یافت نشد.")
                return
            
            # Check if already used
            if test_config.is_used:
                await callback.message.edit_text(
                    f"❌ کانفیگ تستی '{test_config.name}' قبلاً استفاده شده است و قابل حذف نیست.",
                    reply_markup=get_back_keyboard("admin_test_configs")
                )
                await callback.answer()
                return
            
            await session.delete(test_config)
            await session.commit()
            
            await callback.message.edit_text(
                f"✅ کانفیگ تستی '{test_config.name}' با موفقیت حذف شد.",
                reply_markup=get_back_keyboard("admin_test_configs")
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error deleting test config: {e}")
        await callback.message.edit_text(
            "❌ خطا در حذف کانفیگ تستی.",
            reply_markup=get_back_keyboard("admin_test_configs")
        )
        await callback.answer()

@router.callback_query(F.data.startswith("toggle_test_config_"))
async def toggle_test_config(callback: CallbackQuery):
    """Toggle test config active status"""
    if not is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    config_id = int(callback.data.split("_")[3])
    
    try:
        async with AsyncSessionLocal() as session:
            test_config = await session.get(TestConfig, config_id)
            
            if not test_config:
                await callback.answer("❌ کانفیگ تستی یافت نشد.")
                return
            
            test_config.is_active = not test_config.is_active
            await session.commit()
            
            status = "فعال" if test_config.is_active else "غیرفعال"
            await callback.message.edit_text(
                f"✅ وضعیت کانفیگ تستی '{test_config.name}' به '{status}' تغییر یافت.",
                reply_markup=get_back_keyboard("admin_test_configs")
            )
            await callback.answer()
            
    except Exception as e:
        logger.error(f"Error toggling test config: {e}")
        await callback.message.edit_text(
            "❌ خطا در تغییر وضعیت کانفیگ تستی.",
            reply_markup=get_back_keyboard("admin_test_configs")
        )
        await callback.answer()