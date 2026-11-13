from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from models.models import Plan, Purchase, Ticket

def get_main_menu_keyboard():
    """Create main menu keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🧪 تست کانفیگ", callback_data="get_test_config")
    )
    builder.row(
        InlineKeyboardButton(text="🛒 خرید سرویس", callback_data="plans"),
        InlineKeyboardButton(text="📋 سرویس‌های من", callback_data="my_services")
    )
    builder.row(
        InlineKeyboardButton(text="👤 حساب کاربری", callback_data="profile"),
        InlineKeyboardButton(text="💬 پشتیبانی", callback_data="support")
    )
    builder.row(
        InlineKeyboardButton(text="📖 راهنمای اتصال", callback_data="guide")
    )
    return builder.as_markup()


def get_admin_menu_keyboard():
    """Create admin menu keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 داشبورد", callback_data="admin_dashboard"),
        InlineKeyboardButton(text="👥 مدیریت کاربران", callback_data="admin_users")
    )
    builder.row(
        InlineKeyboardButton(text="📨 ارسال همگانی", callback_data="admin_broadcast"),
        InlineKeyboardButton(text="📋 مدیریت تعرفه‌ها", callback_data="admin_plans")
    )
    builder.row(
        InlineKeyboardButton(text="🔧 مدیریت کانفیگ‌ها", callback_data="admin_configs"),
        InlineKeyboardButton(text="💳 مدیریت کارت‌ها", callback_data="admin_cards")
    )
    builder.row(
        InlineKeyboardButton(text="🛒 درخواست‌های خرید", callback_data="admin_purchases"),
        InlineKeyboardButton(text="📢 کانال فروش", callback_data="admin_channel")
    )
    builder.row(
        InlineKeyboardButton(text="⚙️ تنظیمات", callback_data="admin_settings"),
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")
    )
    return builder.as_markup()

def get_plans_keyboard(plans):
    """Create plans selection keyboard"""
    builder = InlineKeyboardBuilder()
    for plan in plans:
        builder.row(
            InlineKeyboardButton(
                text=f"{plan.name} - {plan.price:,} تومان",
                callback_data=f"select_plan_{plan.id}"
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main"))
    return builder.as_markup()

def get_plan_detail_keyboard(plan_id):
    """Create plan detail keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🛒 خرید", callback_data=f"buy_plan_{plan_id}"),
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="plans")
    )
    return builder.as_markup()

def get_purchase_actions_keyboard(purchase_id, is_admin=False):
    """Create purchase action keyboard"""
    builder = InlineKeyboardBuilder()
    if is_admin:
        builder.row(
            InlineKeyboardButton(text="✅ تایید", callback_data=f"approve_purchase_{purchase_id}"),
            InlineKeyboardButton(text="❌ رد", callback_data=f"reject_purchase_{purchase_id}")
        )
    else:
        builder.row(
            InlineKeyboardButton(text="📤 ارسال رسید", callback_data=f"send_receipt_{purchase_id}"),
            InlineKeyboardButton(text="🔙 بازگشت", callback_data="my_services")
        )
    builder.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="my_services"))
    return builder.as_markup()

def get_my_services_keyboard(purchases):
    """Create my services keyboard"""
    builder = InlineKeyboardBuilder()
    for purchase in purchases:
        status_emoji = "✅" if purchase.status.value == "approved" else "⏳"
        builder.row(
            InlineKeyboardButton(
                text=f"{status_emoji} {purchase.plan.name} - {purchase.purchase_date.strftime('%Y-%m-%d')}",
                callback_data=f"service_detail_{purchase.id}"
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main"))
    return builder.as_markup()

def get_service_detail_keyboard(purchase_id, has_config=False):
    """Create service detail keyboard"""
    builder = InlineKeyboardBuilder()
    if has_config:
        builder.row(
            InlineKeyboardButton(text="📋 کپی کانفیگ", callback_data=f"copy_config_{purchase_id}"),
            InlineKeyboardButton(text="🔄 تمدید", callback_data=f"renew_service_{purchase_id}")
        )
    else:
        builder.row(InlineKeyboardButton(text="🔄 تمدید", callback_data=f"renew_service_{purchase_id}"))
    builder.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="my_services"))
    return builder.as_markup()

def get_tickets_keyboard(tickets):
    """Create tickets list keyboard"""
    builder = InlineKeyboardBuilder()
    for ticket in tickets:
        status_emoji = "🔴" if ticket.status.value == "open" else "🟢"
        builder.row(
            InlineKeyboardButton(
                text=f"{status_emoji} {ticket.subject[:30]}...",
                callback_data=f"ticket_detail_{ticket.id}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="➕ تیکت جدید", callback_data="new_ticket"),
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")
    )
    return builder.as_markup()




def get_service_detail_keyboard(purchase_id, has_config=False):
    """Create service detail keyboard"""
    builder = InlineKeyboardBuilder()
    if has_config:
        builder.row(
            InlineKeyboardButton(text="📋 کپی کانفیگ", callback_data=f"copy_config_{purchase_id}"),
            InlineKeyboardButton(text="🔄 تمدید", callback_data=f"renew_service_{purchase_id}")
        )
    else:
        builder.row(InlineKeyboardButton(text="🔄 تمدید", callback_data=f"renew_service_{purchase_id}"))
    builder.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="my_services"))
    return builder.as_markup()

def get_ticket_detail_keyboard(ticket_id):
    """Create ticket detail keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ پاسخ", callback_data=f"reply_ticket_{ticket_id}"),
        InlineKeyboardButton(text="🔒 بستن تیکت", callback_data=f"close_ticket_{ticket_id}")
    )
    builder.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="support"))
    return builder.as_markup()

def get_admin_users_keyboard(users):
    """Create admin users management keyboard"""
    builder = InlineKeyboardBuilder()
    for user in users[:10]:  # Show first 10 users
        status_emoji = "🟢" if user.status.value == "active" else "🔴"
        builder.row(
            InlineKeyboardButton(
                text=f"{status_emoji} {user.first_name or user.username or user.telegram_id}",
                callback_data=f"admin_user_{user.id}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_panel")
    )
    return builder.as_markup()

def get_user_detail_keyboard(user_id):
    """Create user detail management keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🔒 مسدودسازی", callback_data=f"block_user_{user_id}"),
        InlineKeyboardButton(text="🔓 رفع مسدودسازی", callback_data=f"unblock_user_{user_id}")
    )
    builder.row(
        InlineKeyboardButton(text="💬 ارسال پیام", callback_data=f"send_message_to_user_{user_id}"),
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_users")
    )
    return builder.as_markup()

def get_cancel_keyboard():
    """Create cancel keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="❌ لغو", callback_data="cancel_action"))
    return builder.as_markup()

def get_back_keyboard(callback_data="back_to_main"):
    """Create back keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data=callback_data))
    return builder.as_markup()

def get_confirmation_keyboard(action, item_id):
    """Create confirmation keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ تایید", callback_data=f"confirm_{action}_{item_id}"),
        InlineKeyboardButton(text="❌ لغو", callback_data=f"cancel_{action}_{item_id}")
    )
    return builder.as_markup()

def get_admin_plans_keyboard(plans):
    """Create admin plans management keyboard"""
    builder = InlineKeyboardBuilder()
    for plan in plans:
        status_emoji = "🟢" if plan.is_active else "🔴"
        builder.row(
            InlineKeyboardButton(
                text=f"{status_emoji} {plan.name} - {plan.price:,} تومان",
                callback_data=f"admin_plan_{plan.id}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="➕ افزودن تعرفه", callback_data="admin_add_plan"),
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_panel")
    )
    return builder.as_markup()

def get_plan_edit_keyboard(plan_id):
    """Create plan edit keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ ویرایش", callback_data=f"edit_plan_{plan_id}"),
        InlineKeyboardButton(text="🗑️ حذف", callback_data=f"delete_plan_{plan_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 تغییر وضعیت", callback_data=f"toggle_plan_{plan_id}"),
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_plans")
    )
    return builder.as_markup()

def get_admin_configs_keyboard(configs):
    """Create admin configs management keyboard"""
    builder = InlineKeyboardBuilder()
    for config in configs:
        status_emoji = "🟢" if config.is_active else "🔴"
        builder.row(
            InlineKeyboardButton(
                text=f"{status_emoji} {config.name}",
                callback_data=f"admin_config_{config.id}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="➕ افزودن کانفیگ", callback_data="admin_add_config"),
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_panel")
    )
    return builder.as_markup()

def get_config_edit_keyboard(config_id):
    """Create config edit keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ ویرایش", callback_data=f"edit_config_{config_id}"),
        InlineKeyboardButton(text="🗑️ حذف", callback_data=f"delete_config_{config_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 تغییر وضعیت", callback_data=f"toggle_config_{config_id}"),
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_configs")
    )
    return builder.as_markup()

def get_admin_cards_keyboard(cards):
    """Create admin bank cards management keyboard"""
    builder = InlineKeyboardBuilder()
    for card in cards:
        status_emoji = "🟢" if card.is_active else "🔴"
        builder.row(
            InlineKeyboardButton(
                text=f"{status_emoji} {card.card_holder} - {card.bank_name}",
                callback_data=f"admin_card_{card.id}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="➕ افزودن کارت", callback_data="admin_add_card"),
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_panel")
    )
    return builder.as_markup()

def get_card_edit_keyboard(card_id):
    """Create card edit keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ ویرایش", callback_data=f"edit_card_{card_id}"),
        InlineKeyboardButton(text="🗑️ حذف", callback_data=f"delete_card_{card_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 تغییر وضعیت", callback_data=f"toggle_card_{card_id}"),
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_cards")
    )
    return builder.as_markup()

def get_admin_purchases_keyboard(purchases):
    """Create admin purchases management keyboard"""
    builder = InlineKeyboardBuilder()
    for purchase in purchases[:10]:  # Show first 10
        status_emoji = {
            "pending": "⏳",
            "approved": "✅",
            "rejected": "❌",
            "expired": "⏰"
        }.get(purchase.status.value, "❓")
        
        builder.row(
            InlineKeyboardButton(
                text=f"{status_emoji} #{purchase.id} - {purchase.user.first_name or purchase.user.username} - {purchase.plan.name}",
                callback_data=f"admin_purchase_{purchase.id}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_panel")
    )
    return builder.as_markup()

def get_purchase_review_keyboard(purchase_id):
    """Create purchase review keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ تایید خرید", callback_data=f"approve_purchase_{purchase_id}"),
        InlineKeyboardButton(text="❌ رد خرید", callback_data=f"reject_purchase_{purchase_id}")
    )
    builder.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_purchases"))
    return builder.as_markup()

def get_channel_management_keyboard():
    """Create channel management keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📝 ثبت کانال", callback_data="admin_set_channel"),
        InlineKeyboardButton(text="✏️ ویرایش کانال", callback_data="admin_edit_channel")
    )
    builder.row(
        InlineKeyboardButton(text="🗑️ حذف کانال", callback_data="admin_delete_channel"),
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_panel")
    )
    return builder.as_markup()

def get_settings_keyboard():
    """Create settings keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📝 متن خوش‌آمدگویی", callback_data="admin_edit_welcome"),
        InlineKeyboardButton(text="📜 قوانین", callback_data="admin_edit_rules")
    )
    builder.row(
        InlineKeyboardButton(text="📖 راهنمای اتصال", callback_data="admin_edit_guide"),
        InlineKeyboardButton(text="👤 مدیران", callback_data="admin_edit_admins")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_panel")
    )
    return builder.as_markup()

def get_guide_keyboard():
    """Create guide keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📱 Android", callback_data="guide_android"),
        InlineKeyboardButton(text="📱 iPhone", callback_data="guide_iphone")
    )
    builder.row(
        InlineKeyboardButton(text="💻 Windows", callback_data="guide_windows"),
        InlineKeyboardButton(text="💻 MacOS", callback_data="guide_macos")
    )
    builder.row(
        InlineKeyboardButton(text="📖 راهنمای کامل", callback_data="guide_full"),
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")
    )
    return builder.as_markup()


def format_price(price):
    """Format price with commas and remove decimal zeros"""
    try:
        # Convert to float and then to int if it's a whole number
        price_float = float(price)
        if price_float.is_integer():
            return f"{int(price_float):,}"
        else:
            return f"{price_float:,.2f}"
    except:
        return str(price)

def get_plans_keyboard(plans):
    """Create plans selection keyboard"""
    builder = InlineKeyboardBuilder()
    for plan in plans:
        builder.row(
            InlineKeyboardButton(
                text=f"📌 {plan.name} - {format_price(plan.price)} تومان",
                callback_data=f"select_plan_{plan.id}"
            )
        )
    builder.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main"))
    return builder.as_markup()



def get_settings_keyboard():
    """Create settings keyboard with required channels"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📝 متن خوش‌آمدگویی", callback_data="admin_edit_welcome"),
        InlineKeyboardButton(text="📜 قوانین", callback_data="admin_edit_rules")
    )
    builder.row(
        InlineKeyboardButton(text="📖 راهنمای اتصال", callback_data="admin_edit_guide"),
        InlineKeyboardButton(text="👤 مدیران", callback_data="admin_edit_admins")
    )
    builder.row(
        InlineKeyboardButton(text="🔒 کانال‌های اجباری", callback_data="admin_required_channels"),
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_panel")
    )
    return builder.as_markup()

def get_required_channels_keyboard(channels):
    """Create required channels management keyboard"""
    builder = InlineKeyboardBuilder()
    for channel in channels:
        status_emoji = "🟢" if channel.is_active else "🔴"
        builder.row(
            InlineKeyboardButton(
                text=f"{status_emoji} {channel.channel_title or channel.channel_id[:20]}",
                callback_data=f"admin_required_channel_{channel.id}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="➕ افزودن کانال", callback_data="admin_add_required_channel"),
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_settings")
    )
    return builder.as_markup()

def get_channel_edit_keyboard(channel_id):
    """Create channel edit keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="🗑️ حذف", callback_data=f"delete_required_channel_{channel_id}"),
        InlineKeyboardButton(text="🔄 تغییر وضعیت", callback_data=f"toggle_required_channel_{channel_id}")
    )
    builder.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_required_channels"))
    return builder.as_markup()

def get_confirmation_keyboard(action, item_id):
    """Create confirmation keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ تایید", callback_data=f"confirm_{action}_{item_id}"),
        InlineKeyboardButton(text="❌ لغو", callback_data=f"cancel_{action}_{item_id}")
    )
    return builder.as_markup()

def get_join_channel_keyboard(channel_username):
    """Create join channel keyboard"""
    builder = InlineKeyboardBuilder()
    if channel_username:
        builder.row(
            InlineKeyboardButton(
                text="📢 عضویت در کانال",
                url=f"https://t.me/{channel_username.replace('@', '')}"
            )
        )
    builder.row(
        InlineKeyboardButton(text="🔄 بررسی مجدد", callback_data="check_membership")
    )
    return builder.as_markup()


def get_confirmation_keyboard(action, item_id):
    """Create confirmation keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✅ بله، ادامه بده", callback_data=f"confirm_{action}_{item_id}"),
        InlineKeyboardButton(text="❌ نه، لغو کن", callback_data=f"cancel_{action}_{item_id}")
    )
    return builder.as_markup()



def get_settings_keyboard():
    """Create settings keyboard with required channels"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📝 متن خوش‌آمدگویی", callback_data="admin_edit_welcome"),
        InlineKeyboardButton(text="📜 قوانین", callback_data="admin_edit_rules")
    )
    builder.row(
        InlineKeyboardButton(text="📖 راهنمای اتصال", callback_data="admin_edit_guide"),
        InlineKeyboardButton(text="👤 مدیران", callback_data="admin_edit_admins")
    )
    builder.row(
        InlineKeyboardButton(text="🔒 کانال‌های اجباری", callback_data="admin_required_channels"),
        InlineKeyboardButton(text="📢 کانال فروش", callback_data="admin_channel")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_panel")
    )
    return builder.as_markup()



def get_test_configs_keyboard(current_num, total):
    """Create keyboard for test configs"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text=f"📡 دریافت کانفیگ {current_num} از {total}",
            callback_data=f"test_config_{current_num}"
        )
    )
    builder.row(
        InlineKeyboardButton(
            text="⏭️ رد کردن و رفتن به منوی اصلی",
            callback_data="skip_test_configs"
        )
    )
    return builder.as_markup()



def get_admin_menu_keyboard():
    """Create admin menu keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 داشبورد", callback_data="admin_dashboard"),
        InlineKeyboardButton(text="👥 مدیریت کاربران", callback_data="admin_users")
    )
    builder.row(
        InlineKeyboardButton(text="📨 ارسال همگانی", callback_data="admin_broadcast"),
        InlineKeyboardButton(text="📋 مدیریت تعرفه‌ها", callback_data="admin_plans")
    )
    builder.row(
        InlineKeyboardButton(text="🔧 مدیریت کانفیگ‌ها", callback_data="admin_configs"),
        InlineKeyboardButton(text="💳 مدیریت کارت‌ها", callback_data="admin_cards")
    )
    builder.row(
        InlineKeyboardButton(text="🛒 درخواست‌های خرید", callback_data="admin_purchases"),
        InlineKeyboardButton(text="🧪 کانفیگ‌های تستی", callback_data="admin_test_configs")  # اضافه شد
    )
    builder.row(
        InlineKeyboardButton(text="📢 کانال‌ها", callback_data="admin_channel"),
        InlineKeyboardButton(text="⚙️ تنظیمات", callback_data="admin_settings")
    )
    builder.row(
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")
    )
    return builder.as_markup()

def get_test_configs_admin_keyboard(configs):
    """Create test configs management keyboard for admin"""
    builder = InlineKeyboardBuilder()
    
    # Show configs
    for config in configs[:20]:  # Show first 20
        status_emoji = "🟢" if config.is_active else "🔴"
        used_emoji = "✅" if config.is_used else "❌"
        builder.row(
            InlineKeyboardButton(
                text=f"{status_emoji} {used_emoji} {config.name[:30]}",
                callback_data=f"admin_test_config_{config.id}"
            )
        )
    
    if not configs:
        builder.row(
            InlineKeyboardButton(
                text="❌ هیچ کانفیگ تستی ثبت نشده",
                callback_data="no_config"
            )
        )
    
    builder.row(
        InlineKeyboardButton(text="➕ افزودن کانفیگ تستی", callback_data="admin_add_test_config"),
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_panel")
    )
    return builder.as_markup()

def get_test_config_edit_keyboard(config_id):
    """Create test config edit keyboard"""
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="✏️ ویرایش", callback_data=f"edit_test_config_{config_id}"),
        InlineKeyboardButton(text="🗑️ حذف", callback_data=f"delete_test_config_{config_id}")
    )
    builder.row(
        InlineKeyboardButton(text="🔄 تغییر وضعیت", callback_data=f"toggle_test_config_{config_id}"),
        InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_test_configs")
    )
    return builder.as_markup()
