import asyncio
import logging
import os
import re
import random
import enum
from datetime import datetime, timedelta

from aiogram import Bot, Dispatcher, F, BaseMiddleware
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardButton
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.utils.keyboard import InlineKeyboardBuilder
from sqlalchemy import Column, Integer, String, BigInteger, Boolean, DateTime, Text, ForeignKey, Float, Enum, select, func
from sqlalchemy.orm import relationship, declarative_base, sessionmaker, joinedload
from sqlalchemy.sql import func as sql_func
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

# ================= تنظیمات =================
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_IDS = [int(i) for i in os.getenv("ADMIN_IDS", "").split(",") if i.strip()]
DATABASE_URL = "sqlite+aiosqlite:///bot.db"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

Base = declarative_base()
engine = create_async_engine(DATABASE_URL, echo=False)
SessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# ================= مدل‌ها =================
class UserStatus(enum.Enum): ACTIVE="active"; BLOCKED="blocked"
class PurchaseStatus(enum.Enum): PENDING="pending"; APPROVED="approved"; REJECTED="rejected"; EXPIRED="expired"

class User(Base):
    __tablename__='users'; id=Column(Integer,primary_key=True); telegram_id=Column(BigInteger,unique=True); username=Column(String); first_name=Column(String); status=Column(Enum(UserStatus),default=UserStatus.ACTIVE); created_at=Column(DateTime,default=sql_func.now())
    purchases=relationship("Purchase", back_populates="user", cascade="all, delete-orphan")

class Plan(Base):
    __tablename__='plans'; id=Column(Integer,primary_key=True); name=Column(String); volume=Column(String); duration=Column(String); price=Column(Float); description=Column(Text); is_active=Column(Boolean,default=True)
    purchases=relationship("Purchase", back_populates="plan")

class Config(Base):
    __tablename__='configs'; id=Column(Integer,primary_key=True); name=Column(String); address=Column(Text); is_active=Column(Boolean,default=True)
    purchases=relationship("Purchase", back_populates="config")

class Purchase(Base):
    __tablename__='purchases'; id=Column(Integer,primary_key=True); user_id=Column(Integer,ForeignKey('users.id')); plan_id=Column(Integer,ForeignKey('plans.id')); config_id=Column(Integer,ForeignKey('configs.id')); amount=Column(Float); status=Column(Enum(PurchaseStatus),default=PurchaseStatus.PENDING); purchase_date=Column(DateTime,default=sql_func.now()); expiry_date=Column(DateTime)
    user=relationship("User", back_populates="purchases"); plan=relationship("Plan", back_populates="purchases"); config=relationship("Config", back_populates="purchases")

# ================= ابزارها =================
def is_admin(uid): return uid in ADMIN_IDS
def format_price(p):
    try: return f"{int(float(p)):,}"
    except: return str(p)
def parse_duration(s):
    try:
        s=str(s).strip().lower()
        for w,m in [('روز',1),('ماه',30),('سال',365),('day',1),('month',30),('year',365)]:
            if w in s:
                n=re.findall(r'\d+',s)
                if n: return int(n[0])*m
        n=re.findall(r'\d+',s); return int(n[0]) if n else 30
    except: return 30

# ================= کیبوردها =================
def kb_main():
    b=InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="🧪 تست کانفیگ", callback_data="get_test_config"))
    b.row(InlineKeyboardButton(text="🛒 خرید", callback_data="plans"), InlineKeyboardButton(text="📋 سرویس‌ها", callback_data="my_services"))
    b.row(InlineKeyboardButton(text="👤 پروفایل", callback_data="profile"), InlineKeyboardButton(text="💬 پشتیبانی", callback_data="support"))
    b.row(InlineKeyboardButton(text="📖 راهنما", callback_data="guide"))
    return b.as_markup()
def kb_admin():
    b=InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="📊 داشبورد", callback_data="admin_dashboard"), InlineKeyboardButton(text="👥 کاربران", callback_data="admin_users"))
    b.row(InlineKeyboardButton(text="📋 تعرفه‌ها", callback_data="admin_plans"), InlineKeyboardButton(text="💳 کارت‌ها", callback_data="admin_cards"))
    b.row(InlineKeyboardButton(text="🛒 خریدها", callback_data="admin_purchases"))
    b.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main"))
    return b.as_markup()
def kb_back(cb="back_to_main"): return InlineKeyboardBuilder().row(InlineKeyboardButton(text="🔙 بازگشت", callback_data=cb)).as_markup()
def kb_cancel(): return InlineKeyboardBuilder().row(InlineKeyboardButton(text="❌ لغو", callback_data="cancel_action")).as_markup()
def kb_plans(plans):
    b=InlineKeyboardBuilder()
    for p in plans: b.row(InlineKeyboardButton(text=f"📌 {p.name} - {format_price(p.price)} ت", callback_data=f"sel_plan_{p.id}"))
    b.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main"))
    return b.as_markup()
def kb_plan_detail(pid): return InlineKeyboardBuilder().row(InlineKeyboardButton(text="🛒 خرید", callback_data=f"buy_{pid}"), InlineKeyboardButton(text="🔙 بازگشت", callback_data="plans")).as_markup()
def kb_admin_plans(plans):
    b=InlineKeyboardBuilder()
    for p in plans: b.row(InlineKeyboardButton(text=f"{'🟢' if p.is_active else '🔴'} {p.name}", callback_data=f"a_plan_{p.id}"))
    b.row(InlineKeyboardButton(text="➕ افزودن", callback_data="add_plan"), InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_panel"))
    return b.as_markup()
def kb_plan_edit(pid): return InlineKeyboardBuilder().row(InlineKeyboardButton(text="🗑️ حذف", callback_data=f"del_plan_{pid}"), InlineKeyboardButton(text="🔄 وضعیت", callback_data=f"tog_plan_{pid}")).row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_plans")).as_markup()
def kb_my_services(purchases):
    b=InlineKeyboardBuilder()
    for p in purchases: b.row(InlineKeyboardButton(text=f"{'✅' if p.status.value=='approved' else '⏳'} {p.plan.name} - {p.purchase_date.strftime('%m-%d')}", callback_data=f"svc_{p.id}"))
    b.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main"))
    return b.as_markup()
def kb_svc_detail(pid, has_cfg=False):
    b=InlineKeyboardBuilder()
    if has_cfg: b.row(InlineKeyboardButton(text="📋 کپی", callback_data=f"cp_{pid}"))
    b.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="my_services"))
    return b.as_markup()
def kb_purchase_actions(pid): return InlineKeyboardBuilder().row(InlineKeyboardButton(text="✅ تایید", callback_data=f"appr_{pid}"), InlineKeyboardButton(text="❌ رد", callback_data=f"rej_{pid}")).as_markup()
def kb_admin_users(users):
    b=InlineKeyboardBuilder()
    for u in users[:10]: b.row(InlineKeyboardButton(text=f"{'🟢' if u.status.value=='active' else '🔴'} {u.first_name or u.username or u.telegram_id}", callback_data=f"a_user_{u.id}"))
    b.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_panel"))
    return b.as_markup()
def kb_user_detail(uid): return InlineKeyboardBuilder().row(InlineKeyboardButton(text="🔒 مسدود", callback_data=f"blk_{uid}"), InlineKeyboardButton(text="🔓 رفع", callback_data=f"unblk_{uid}")).row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_users")).as_markup()
def kb_admin_cards(cards):
    b=InlineKeyboardBuilder()
    for c in cards: b.row(InlineKeyboardButton(text=f"{'🟢' if c.is_active else '🔴'} {c.bank_name}", callback_data=f"a_card_{c.id}"))
    b.row(InlineKeyboardButton(text="➕ افزودن", callback_data="add_card"), InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_panel"))
    return b.as_markup()
def kb_card_edit(cid): return InlineKeyboardBuilder().row(InlineKeyboardButton(text="🗑️ حذف", callback_data=f"del_card_{cid}"), InlineKeyboardButton(text="🔄 وضعیت", callback_data=f"tog_card_{cid}")).row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_cards")).as_markup()
def kb_guide():
    b=InlineKeyboardBuilder()
    b.row(InlineKeyboardButton(text="📱 Android", callback_data="g_android"), InlineKeyboardButton(text="📱 iPhone", callback_data="g_iphone"))
    b.row(InlineKeyboardButton(text="💻 Windows", callback_data="g_windows"), InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main"))
    return b.as_markup()
def kb_join(username):
    b=InlineKeyboardBuilder()
    if username: b.row(InlineKeyboardButton(text="📢 عضویت", url=f"https://t.me/{username.replace('@', '')}"))
    b.row(InlineKeyboardButton(text="🔄 بررسی", callback_data="check_member"))
    return b.as_markup()

# ================= ربات =================
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode='HTML'))
dp = Dispatcher(storage=MemoryStorage())

class S(StatesGroup):
    tc_name=State(); tc_addr=State(); plan_name=State(); plan_vol=State(); plan_dur=State(); plan_price=State(); plan_desc=State(); card_holder=State(); card_num=State(); card_bank=State(); receipt=State(); rej_reason=State()

@dp.message(CommandStart())
async def cmd_start(msg: Message, state: FSMContext):
    await state.clear()
    async with SessionLocal() as s:
        res = await s.execute(select(User).where(User.telegram_id == msg.from_user.id))
        u = res.scalar_one_or_none()
        if not u:
            s.add(User(telegram_id=msg.from_user.id, username=msg.from_user.username, first_name=msg.from_user.first_name))
            await s.commit()
    kb = kb_admin() if is_admin(msg.from_user.id) else kb_main()
    await msg.answer(f"👋 خوش آمدید!\n\n🆔 {msg.from_user.id}", reply_markup=kb)

@dp.message(F.text == "/admin")
async def admin_cmd(msg: Message):
    if is_admin(msg.from_user.id): await msg.answer("🔐 پنل ادمین:", reply_markup=kb_admin())

@dp.callback_query(F.data == "back_to_main")
async def cb_back(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    kb = kb_admin() if is_admin(cb.from_user.id) else kb_main()
    try: await cb.message.edit_text("🏠 منوی اصلی:", reply_markup=kb)
    except: await cb.message.answer("🏠 منوی اصلی:", reply_markup=kb)
    await cb.answer()

@dp.callback_query(F.data == "cancel_action")
async def cb_cancel(cb: CallbackQuery, state: FSMContext):
    await state.clear()
    await cb.message.edit_text("❌ لغو شد.", reply_markup=kb_back())
    await cb.answer()

@dp.callback_query(F.data == "admin_panel")
async def cb_admin_panel(cb: CallbackQuery):
    if is_admin(cb.from_user.id): await cb.message.edit_text("🔐 پنل ادمین:", reply_markup=kb_admin())
    await cb.answer()

# ================= منوی کاربر =================
@dp.callback_query(F.data == "plans")
async def cb_plans(cb: CallbackQuery):
    async with SessionLocal() as s:
        res = await s.execute(select(Plan).where(Plan.is_active == True))
        plans = res.scalars().all()
    if not plans:
        await cb.message.edit_text("❌ تعرفه‌ای نیست.", reply_markup=kb_back()); await cb.answer(); return
    txt = "🛒 <b>خرید سرویس</b>\n\n"
    for p in plans: txt += f"🔹 {p.name}\n💾 {p.volume} | ⏰ {p.duration}\n💰 {format_price(p.price)} ت\n\n"
    await cb.message.edit_text(txt, reply_markup=kb_plans(plans)); await cb.answer()

@dp.callback_query(F.data.startswith("sel_plan_"))
async def cb_sel_plan(cb: CallbackQuery):
    pid = int(cb.data.split("_")[2])
    async with SessionLocal() as s: p = await s.get(Plan, pid)
    if not p: await cb.answer("❌"); return
    txt = f"📋 <b>{p.name}</b>\n\n💾 {p.volume}\n⏰ {p.duration}\n💰 {format_price(p.price)} تومان\n📝 {p.description or '—'}"
    await cb.message.edit_text(txt, reply_markup=kb_plan_detail(pid)); await cb.answer()

@dp.callback_query(F.data.startswith("buy_"))
async def cb_buy(cb: CallbackQuery, state: FSMContext):
    pid = int(cb.data.split("_")[1])
    async with SessionLocal() as s:
        res = await s.execute(select(User).where(User.telegram_id == cb.from_user.id))
        u = res.scalar_one_or_none()
        if not u or u.status != UserStatus.ACTIVE: await cb.answer("❌"); return
        p = await s.get(Plan, pid)
        res = await s.execute(select(BankCard).where(BankCard.is_active == True))
        cards = res.scalars().all()
        if not cards:
            await cb.message.edit_text("❌ کارت بانکی موجود نیست.", reply_markup=kb_back("plans")); await cb.answer(); return
        pur = Purchase(user_id=u.id, plan_id=p.id, amount=float(p.price), status=PurchaseStatus.PENDING)
        s.add(pur); await s.commit(); await s.refresh(pur)
        await state.update_data(pid=pur.id, pname=p.name, pprice=float(p.price))
    card_txt = "".join([f"🏦 {c.bank_name}\n👤 {c.card_holder}\n🔢 <code>{c.card_number}</code>\n\n" for c in cards])
    txt = f"💰 مبلغ: <b>{format_price(p.price)}</b> تومان\n📋 {p.name}\n\n💳 واریز:\n\n{card_txt}📸 بعد از واریز، عکس رسید را بفرست."
    await cb.message.edit_text(txt, reply_markup=kb_cancel()); await state.set_state(S.receipt); await cb.answer("رسید را بفرست")

@dp.message(S.receipt, F.photo)
async def on_receipt_photo(msg: Message, state: FSMContext):
    d = await state.get_data(); pid = d.get('pid')
    if not pid: await msg.answer("❌", reply_markup=kb_back()); await state.clear(); return
    photo = msg.photo[-1]; f = await msg.bot.get_file(photo.file_id)
    path = f"receipts/r_{pid}.jpg"; os.makedirs("receipts", exist_ok=True); await msg.bot.download_file(f.file_path, path)
    async with SessionLocal() as s:
        p = await s.get(Purchase, pid)
        if p: p.receipt_image = path; await s.commit()
    for aid in ADMIN_IDS:
        try: await msg.bot.send_photo(aid, FSInputFile(path), caption=f"📥 خرید جدید\n🆔 #{pid}\n👤 {msg.from_user.first_name}", reply_markup=kb_purchase_actions(pid))
        except: pass
    await msg.answer("✅ رسید ارسال شد.", reply_markup=kb_back("my_services")); await state.clear()

@dp.message(S.receipt, F.text)
async def on_receipt_text(msg: Message, state: FSMContext):
    d = await state.get_data(); pid = d.get('pid')
    if not pid: await msg.answer("❌", reply_markup=kb_back()); await state.clear(); return
    for aid in ADMIN_IDS:
        try: await msg.bot.send_message(aid, f"📥 خرید جدید (متن)\n🆔 #{pid}\n📝 {msg.text[:300]}", reply_markup=kb_purchase_actions(pid))
        except: pass
    await msg.answer("✅ رسید ثبت شد.", reply_markup=kb_back("my_services")); await state.clear()

@dp.message(S.receipt)
async def on_receipt_invalid(msg: Message): await msg.answer("❌ عکس یا متن بفرست.", reply_markup=kb_cancel())

@dp.callback_query(F.data.startswith("appr_"))
async def cb_approve(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): await cb.answer("⛔"); return
    pid = int(cb.data.split("_")[1])
    async with SessionLocal() as s:
        res = await s.execute(select(Purchase).options(joinedload(Purchase.plan), joinedload(Purchase.user)).where(Purchase.id == pid))
        p = res.scalar_one_or_none()
        if not p: await cb.answer("❌"); return
        res = await s.execute(select(Config).where(Config.is_active == True))
        cfgs = res.scalars().all()
        if not cfgs: await cb.message.answer("❌ کانفیگ موجود نیست."); await cb.answer(); return
        cfg = cfgs[0]; p.config_id = cfg.id; p.expiry_date = datetime.now() + timedelta(days=parse_duration(p.plan.duration)); p.status = PurchaseStatus.APPROVED
        await s.commit()
        try: await cb.bot.send_message(p.user.telegram_id, f"🔐 کانفیگ شما\n\n<code>{cfg.address}</code>")
        except: pass
    await cb.message.answer(f"✅ خرید #{pid} تایید شد.", reply_markup=kb_back("admin_purchases")); await cb.answer("✅")

@dp.callback_query(F.data.startswith("rej_"))
async def cb_reject(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id): await cb.answer("⛔"); return
    pid = int(cb.data.split("_")[1]); await state.update_data(pid=pid)
    await cb.message.answer("❌ دلیل رد:", reply_markup=kb_cancel()); await state.set_state(S.rej_reason); await cb.answer()

@dp.message(S.rej_reason, F.text)
async def on_rej(msg: Message, state: FSMContext):
    d = await state.get_data(); pid = d.get('pid')
    async with SessionLocal() as s:
        res = await s.execute(select(Purchase).options(joinedload(Purchase.user)).where(Purchase.id == pid))
        p = res.scalar_one_or_none()
        if p:
            p.status = PurchaseStatus.REJECTED; p.rejection_reason = msg.text; await s.commit()
            try: await msg.bot.send_message(p.user.telegram_id, f"❌ خرید رد شد.\n📋 دلیل: {msg.text}", reply_markup=kb_back())
            except: pass
    await msg.answer(f"✅ خرید #{pid} رد شد.", reply_markup=kb_back("admin_purchases")); await state.clear()

@dp.callback_query(F.data == "my_services")
async def cb_my_svc(cb: CallbackQuery):
    async with SessionLocal() as s:
        res = await s.execute(select(User).where(User.telegram_id == cb.from_user.id))
        u = res.scalar_one_or_none()
        res = await s.execute(select(Purchase).options(joinedload(Purchase.plan)).where(Purchase.user_id == u.id).order_by(Purchase.purchase_date.desc()))
        ps = res.scalars().all()
    if not ps: await cb.message.edit_text("📋 سرویسی نداری.", reply_markup=kb_back()); await cb.answer(); return
    await cb.message.edit_text("📋 سرویس‌های من:", reply_markup=kb_my_services(ps)); await cb.answer()

@dp.callback_query(F.data.startswith("svc_"))
async def cb_svc_detail(cb: CallbackQuery):
    pid = int(cb.data.split("_")[1])
    async with SessionLocal() as s:
        res = await s.execute(select(Purchase).options(joinedload(Purchase.plan), joinedload(Purchase.config), joinedload(Purchase.user)).where(Purchase.id == pid))
        p = res.scalar_one_or_none()
    if not p or (p.user.telegram_id != cb.from_user.id and not is_admin(cb.from_user.id)): await cb.answer("⛔"); return
    st = {"pending":"⏳","approved":"✅","rejected":"❌","expired":"⏰"}.get(p.status.value, "?")
    txt = f"📋 <b>{p.plan.name}</b>\n\n📅 {p.purchase_date.strftime('%Y-%m-%d')}\n📊 {st}\n💰 {format_price(p.amount)} ت\n"
    has_cfg = False
    if p.config and p.status == PurchaseStatus.APPROVED: txt += f"\n🔐 <code>{p.config.address}</code>"; has_cfg = True
    await cb.message.edit_text(txt, reply_markup=kb_svc_detail(pid, has_cfg)); await cb.answer()

@dp.callback_query(F.data.startswith("cp_"))
async def cb_copy(cb: CallbackQuery):
    pid = int(cb.data.split("_")[1])
    async with SessionLocal() as s:
        res = await s.execute(select(Purchase).options(joinedload(Purchase.config)).where(Purchase.id == pid))
        p = res.scalar_one_or_none()
    if not p or not p.config: await cb.answer("❌"); return
    await cb.message.edit_text(f"🔐 <code>{p.config.address}</code>", reply_markup=kb_back("my_services")); await cb.answer()

@dp.callback_query(F.data == "profile")
async def cb_profile(cb: CallbackQuery):
    async with SessionLocal() as s:
        res = await s.execute(select(User).where(User.telegram_id == cb.from_user.id))
        u = res.scalar_one_or_none()
    if not u: await cb.answer("❌"); return
    txt = f"👤 <b>پروفایل</b>\n\n🆔 {u.telegram_id}\n👤 {u.first_name or '?'}\n📝 @{u.username or '—'}\n📅 {u.created_at.strftime('%Y-%m-%d')}\n📊 {'✅' if u.status.value == 'active' else '🔴'}"
    await cb.message.edit_text(txt, reply_markup=kb_back()); await cb.answer()

@dp.callback_query(F.data == "guide")
async def cb_guide(cb: CallbackQuery): await cb.message.edit_text("📖 راهنما:", reply_markup=kb_guide()); await cb.answer()

@dp.callback_query(F.data.startswith("g_"))
async def cb_guide_detail(cb: CallbackQuery):
    plat = cb.data.split("_")[1]
    txts = {"android":"📱 <b>Android</b>\n\n1. V2RayNG نصب کن\n2. کانفیگ رو وارد کن\n3. وصل شو", "iphone":"📱 <b>iPhone</b>\n\n1. Shadowrocket نصب کن\n2. کانفیگ رو وارد کن\n3. وصل شو", "windows":"💻 <b>Windows</b>\n\n1. V2RayN نصب کن\n2. کانفیگ رو وارد کن\n3. وصل شو"}
    await cb.message.edit_text(txts.get(plat, "—"), reply_markup=kb_back("guide")); await cb.answer()

@dp.callback_query(F.data == "support")
async def cb_support(cb: CallbackQuery): await cb.message.edit_text("🎧 پشتیبانی:\n\n👤 @di_izirvpn", reply_markup=kb_back()); await cb.answer()

@dp.callback_query(F.data == "get_test_config")
async def cb_get_tc(cb: CallbackQuery):
    async with SessionLocal() as s:
        res = await s.execute(select(User).where(User.telegram_id == cb.from_user.id)); u = res.scalar_one_or_none()
        res = await s.execute(select(TestConfig).where(TestConfig.is_active == True, TestConfig.is_used == False))
        avail = res.scalars().all()
        if not avail: await cb.message.edit_text("❌ کانفیگ تستی موجود نیست.", reply_markup=kb_back()); await cb.answer(); return
        tc = random.choice(avail); tc.is_used = True; tc.used_by_user_id = u.id; tc.used_at = datetime.now(); await s.commit()
    await cb.message.edit_text(f"🧪 کانفیگ تستی\n\n<code>{tc.address}</code>\n\n⚠️ یکبار مصرف", reply_markup=kb_back()); await cb.answer("✅")

@dp.callback_query(F.data == "check_member")
async def cb_check_member(cb: CallbackQuery): await cb.message.edit_text("✅ بررسی شد.", reply_markup=kb_main()); await cb.answer("✅")

# ================= پنل ادمین =================
@dp.callback_query(F.data == "admin_dashboard")
async def cb_dash(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): await cb.answer("⛔"); return
    async with SessionLocal() as s:
        tu = (await s.execute(select(func.count(User.id)))).scalar()
        tr = (await s.execute(select(func.sum(Purchase.amount)).where(Purchase.status == PurchaseStatus.APPROVED))).scalar() or 0
    await cb.message.edit_text(f"📊 آمار\n👥 کاربران: {tu}\n💰 فروش: {format_price(tr)} ت", reply_markup=kb_back("admin_panel")); await cb.answer()

@dp.callback_query(F.data == "admin_users")
async def cb_users(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): await cb.answer("⛔"); return
    async with SessionLocal() as s:
        res = await s.execute(select(User).order_by(User.created_at.desc()).limit(20)); us = res.scalars().all()
    await cb.message.edit_text("👥 کاربران:", reply_markup=kb_admin_users(us)); await cb.answer()

@dp.callback_query(F.data.startswith("a_user_"))
async def cb_user_detail(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): await cb.answer("⛔"); return
    uid = int(cb.data.split("_")[2])
    async with SessionLocal() as s:
        res = await s.execute(select(User).where(User.id == uid)); u = res.scalar_one_or_none()
    if not u: await cb.answer("❌"); return
    await cb.message.edit_text(f"👤 {u.first_name or '?'}\n🆔 {u.telegram_id}\n📊 {'✅' if u.status.value == 'active' else '🔴'}", reply_markup=kb_user_detail(uid)); await cb.answer()

@dp.callback_query(F.data.startswith("blk_"))
async def cb_block(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): await cb.answer("⛔"); return
    uid = int(cb.data.split("_")[1])
    async with SessionLocal() as s:
        res = await s.execute(select(User).where(User.id == uid)); u = res.scalar_one_or_none()
        if u: u.status = UserStatus.BLOCKED; await s.commit()
    await cb.message.edit_text("✅ مسدود شد.", reply_markup=kb_back("admin_users")); await cb.answer()

@dp.callback_query(F.data.startswith("unblk_"))
async def cb_unblock(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): await cb.answer("⛔"); return
    uid = int(cb.data.split("_")[1])
    async with SessionLocal() as s:
        res = await s.execute(select(User).where(User.id == uid)); u = res.scalar_one_or_none()
        if u: u.status = UserStatus.ACTIVE; await s.commit()
    await cb.message.edit_text("✅ رفع شد.", reply_markup=kb_back("admin_users")); await cb.answer()

@dp.callback_query(F.data == "admin_plans")
async def cb_admin_plans(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): await cb.answer("⛔"); return
    async with SessionLocal() as s:
        res = await s.execute(select(Plan).order_by(Plan.id.desc())); ps = res.scalars().all()
    await cb.message.edit_text("📋 تعرفه‌ها:", reply_markup=kb_admin_plans(ps)); await cb.answer()

@dp.callback_query(F.data == "add_plan")
async def cb_add_plan(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id): await cb.answer("⛔"); return
    await cb.message.edit_text("📛 نام تعرفه:", reply_markup=kb_cancel()); await state.set_state(S.plan_name); await cb.answer()

@dp.message(S.plan_name, F.text)
async def on_plan_name(msg: Message, state: FSMContext): await state.update_data(p_name=msg.text); await msg.answer("💾 حجم:", reply_markup=kb_cancel()); await state.set_state(S.plan_vol)
@dp.message(S.plan_vol, F.text)
async def on_plan_vol(msg: Message, state: FSMContext): await state.update_data(p_vol=msg.text); await msg.answer("⏰ مدت:", reply_markup=kb_cancel()); await state.set_state(S.plan_dur)
@dp.message(S.plan_dur, F.text)
async def on_plan_dur(msg: Message, state: FSMContext): await state.update_data(p_dur=msg.text); await msg.answer("💰 قیمت:", reply_markup=kb_cancel()); await state.set_state(S.plan_price)
@dp.message(S.plan_price, F.text)
async def on_plan_price(msg: Message, state: FSMContext):
    try: p = float(msg.text.replace(',', '').strip())
    except: await msg.answer("❌ عدد وارد کن:", reply_markup=kb_cancel()); return
    await state.update_data(p_price=p); await msg.answer("📝 توضیحات (یا 'بدون'):", reply_markup=kb_cancel()); await state.set_state(S.plan_desc)
@dp.message(S.plan_desc, F.text)
async def on_plan_desc(msg: Message, state: FSMContext):
    d = await state.get_data()
    async with SessionLocal() as s:
        s.add(Plan(name=d['p_name'], volume=d['p_vol'], duration=d['p_dur'], price=d['p_price'], description=None if msg.text == "بدون" else msg.text)); await s.commit()
    await msg.answer("✅ تعرفه ساخته شد.", reply_markup=kb_back("admin_plans")); await state.clear()

@dp.callback_query(F.data.startswith("a_plan_"))
async def cb_plan_detail(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): await cb.answer("⛔"); return
    pid = int(cb.data.split("_")[2])
    async with SessionLocal() as s: p = await s.get(Plan, pid)
    if not p: await cb.answer("❌"); return
    await cb.message.edit_text(f"📛 {p.name}\n💾 {p.volume}\n⏰ {p.duration}\n💰 {format_price(p.price)} ت", reply_markup=kb_plan_edit(pid)); await cb.answer()

@dp.callback_query(F.data.startswith("del_plan_"))
async def cb_del_plan(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): await cb.answer("⛔"); return
    pid = int(cb.data.split("_")[2])
    async with SessionLocal() as s:
        res = await s.execute(select(Plan).where(Plan.id == pid)); p = res.scalar_one_or_none()
        if p: await s.delete(p); await s.commit()
    await cb.message.edit_text("✅ حذف شد.", reply_markup=kb_back("admin_plans")); await cb.answer()

@dp.callback_query(F.data.startswith("tog_plan_"))
async def cb_tog_plan(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): await cb.answer("⛔"); return
    pid = int(cb.data.split("_")[2])
    async with SessionLocal() as s:
        res = await s.execute(select(Plan).where(Plan.id == pid)); p = res.scalar_one_or_none()
        if p: p.is_active = not p.is_active; await s.commit()
    await cb.message.edit_text("✅ تغییر کرد.", reply_markup=kb_back("admin_plans")); await cb.answer()

@dp.callback_query(F.data == "admin_purchases")
async def cb_admin_purchases(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): await cb.answer("⛔"); return
    async with SessionLocal() as s:
        res = await s.execute(select(Purchase).options(joinedload(Purchase.user), joinedload(Purchase.plan)).where(Purchase.status == PurchaseStatus.PENDING).limit(10))
        ps = res.scalars().all()
    if not ps: await cb.message.edit_text("✅ درخواستی نیست.", reply_markup=kb_back("admin_panel")); await cb.answer(); return
    b = InlineKeyboardBuilder()
    for p in ps: b.row(InlineKeyboardButton(text=f"⏳ #{p.id} - {p.user.first_name or '?'} - {format_price(p.amount)} ت", callback_data=f"pr_{p.id}"))
    b.row(InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_panel"))
    await cb.message.edit_text("🛒 در انتظار:", reply_markup=b.as_markup()); await cb.answer()

@dp.callback_query(F.data.startswith("pr_"))
async def cb_purchase_review(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): await cb.answer("⛔"); return
    pid = int(cb.data.split("_")[1])
    await cb.message.edit_text(f"خرید #{pid}", reply_markup=kb_purchase_actions(pid)); await cb.answer()

@dp.callback_query(F.data == "admin_cards")
async def cb_admin_cards(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): await cb.answer("⛔"); return
    async with SessionLocal() as s:
        res = await s.execute(select(BankCard).order_by(BankCard.id.desc())); cs = res.scalars().all()
    await cb.message.edit_text("💳 کارت‌ها:", reply_markup=kb_admin_cards(cs)); await cb.answer()

@dp.callback_query(F.data == "add_card")
async def cb_add_card(cb: CallbackQuery, state: FSMContext):
    if not is_admin(cb.from_user.id): await cb.answer("⛔"); return
    await cb.message.edit_text("👤 نام دارنده:", reply_markup=kb_cancel()); await state.set_state(S.card_holder); await cb.answer()

@dp.message(S.card_holder, F.text)
async def on_card_holder(msg: Message, state: FSMContext): await state.update_data(c_holder=msg.text); await msg.answer("🔢 شماره کارت:", reply_markup=kb_cancel()); await state.set_state(S.card_num)
@dp.message(S.card_num, F.text)
async def on_card_num(msg: Message, state: FSMContext):
    num = msg.text.replace(' ', '').replace('-', '')
    if len(num) != 16 or not num.isdigit(): await msg.answer("❌ 16 رقم:", reply_markup=kb_cancel()); return
    await state.update_data(c_num=num); await msg.answer("🏦 نام بانک:", reply_markup=kb_cancel()); await state.set_state(S.card_bank)
@dp.message(S.card_bank, F.text)
async def on_card_bank(msg: Message, state: FSMContext):
    d = await state.get_data()
    async with SessionLocal() as s:
        s.add(BankCard(card_holder=d['c_holder'], card_number=d['c_num'], bank_name=msg.text)); await s.commit()
    await msg.answer("✅ کارت ساخته شد.", reply_markup=kb_back("admin_cards")); await state.clear()

@dp.callback_query(F.data.startswith("del_card_"))
async def cb_del_card(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): await cb.answer("⛔"); return
    cid = int(cb.data.split("_")[2])
    async with SessionLocal() as s:
        res = await s.execute(select(BankCard).where(BankCard.id == cid)); c = res.scalar_one_or_none()
        if c: await s.delete(c); await s.commit()
    await cb.message.edit_text("✅ حذف شد.", reply_markup=kb_back("admin_cards")); await cb.answer()

@dp.callback_query(F.data.startswith("tog_card_"))
async def cb_tog_card(cb: CallbackQuery):
    if not is_admin(cb.from_user.id): await cb.answer("⛔"); return
    cid = int(cb.data.split("_")[2])
    async with SessionLocal() as s:
        res = await s.execute(select(BankCard).where(BankCard.id == cid)); c = res.scalar_one_or_none()
        if c: c.is_active = not c.is_active; await s.commit()
    await cb.message.edit_text("✅ تغییر کرد.", reply_markup=kb_back("admin_cards")); await cb.answer()

# ================= راه‌اندازی =================
async def main():
    async with engine.begin() as conn: await conn.run_sync(Base.metadata.create_all)
    logger.info("Bot started!")
    await dp.start_polling(bot)

if __name__ == "__main__": asyncio.run(main())
