import logging
import os
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    ReplyKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes, ConversationHandler
)
from database import Database

logging.basicConfig(format='%(asctime)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# ╔══════════════════════════════════════════╗
# ║           MONIX BOT SOZLAMALARI          ║
# ╚══════════════════════════════════════════╝
BOT_TOKEN          = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN")
ADMIN_ID           = int(os.getenv("ADMIN_ID", "123456789"))
BOT_USERNAME       = os.getenv("BOT_USERNAME", "monixbonusbot")
CHANNEL_USERNAME   = os.getenv("CHANNEL_USERNAME", "@monixyangiliklarkanali")
CHANNEL_LINK       = os.getenv("CHANNEL_LINK", "https://t.me/monixyangiliklarkanali")
PROOF_CHANNEL      = os.getenv("PROOF_CHANNEL", "@monixtolovlarkanali")
PROOF_CHANNEL_LINK = os.getenv("PROOF_CHANNEL_LINK", "https://t.me/monixtolovlarkanali")
ADMIN_USERNAME     = os.getenv("ADMIN_USERNAME", "@adminusername")
BONUS_PER_REFERRAL = int(os.getenv("BONUS_PER_REFERRAL", "7000"))
MIN_WITHDRAW       = int(os.getenv("MIN_WITHDRAW", "100000"))

db = Database("monix.db")
WAITING_CARD = 1

# ──────────────────────────────────────────────
# KLAVIATURALAR
# ──────────────────────────────────────────────

def main_keyboard():
    return ReplyKeyboardMarkup(
        [
            ["💸 PUL ISHLASH 💸"],
            ["💰 BALANS", "✅ BONUS OLISH", "🗂 PUL YECHISH"],
            ["📢 Monix Kanal", "💳 To'lovlar"],
            ["👤 ADMIN"],
        ],
        resize_keyboard=True
    )

def sub_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Monix Kanal — Obuna bo'lish", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ Obuna bo'ldim — Tekshirish", callback_data="check_sub")],
    ])

def withdraw_keyboard():
    return ReplyKeyboardMarkup(
        [["✅ Yuborish"], ["🚫 Bekor qilish"]],
        resize_keyboard=True, one_time_keyboard=True
    )

# ──────────────────────────────────────────────
# OBUNA TEKSHIRISH
# ──────────────────────────────────────────────

async def is_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception:
        return False

async def require_sub(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not await is_subscribed(update.effective_user.id, context):
        await update.message.reply_text(
            "⛔️ <b>Botdan foydalanish uchun kanalga obuna bo'lishingiz shart!</b>\n\n"
            "📢 Quyidagi tugmani bosib <b>Monix Kanal</b>ga obuna bo'ling,\n"
            "so'ng «✅ Obuna bo'ldim» tugmasini bosing.",
            reply_markup=sub_keyboard(),
            parse_mode="HTML"
        )
        return False
    return True

# ──────────────────────────────────────────────
# START
# ──────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args
    referrer_id = None

    if args and args[0].startswith("r"):
        try:
            referrer_id = int(args[0][1:])
            if referrer_id == user.id:
                referrer_id = None
        except ValueError:
            pass

    is_new = db.register_user(user.id, user.full_name, user.username or "", referrer_id)

    if is_new and referrer_id:
        db.add_referral(referrer_id, user.id)
        db.add_balance(referrer_id, BONUS_PER_REFERRAL)
        try:
            ref_count = db.get_referral_count(referrer_id)
            ref_bal   = db.get_user(referrer_id)["balance"]
            await context.bot.send_message(
                chat_id=referrer_id,
                text=(
                    f"🎉 <b>Yangi do'stingiz qo'shildi!</b>\n\n"
                    f"👤 <b>{user.full_name}</b> havolangiz orqali kirdi\n"
                    f"💰 <b>+{BONUS_PER_REFERRAL:,} so'm</b> balansingizga qo'shildi!\n\n"
                    f"📊 Jami taklif: <b>{ref_count} ta</b>\n"
                    f"💵 Balans: <b>{ref_bal:,} so'm</b>"
                ),
                parse_mode="HTML"
            )
        except Exception:
            pass

    subscribed = await is_subscribed(user.id, context)
    if not subscribed:
        await update.message.reply_text(
            "👋 <b>ASSALOMU ALAYKUM!</b>\n\n"
            "🤖 <b>MONIX BONUS</b> botiga xush kelibsiz!\n\n"
            "━━━━━━━━━━━━━━━━━━━━\n"
            "📢 Botdan to'liq foydalanish uchun\n"
            "<b>Monix Kanal</b>ga obuna bo'lishingiz shart!\n"
            "━━━━━━━━━━━━━━━━━━━━\n\n"
            "👇 Quyidagi tugmani bosing:",
            reply_markup=sub_keyboard(),
            parse_mode="HTML"
        )
        return

    await _show_main_menu(update, context)


async def check_sub_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user  = query.from_user
    await query.answer()

    if not await is_subscribed(user.id, context):
        await query.answer(
            "❌ Siz hali obuna bo'lmagansiz!\nIltimos avval obuna bo'ling.",
            show_alert=True
        )
        return

    await query.message.delete()
    user_data = db.get_user(user.id)
    balance   = user_data["balance"] if user_data else 0
    ref_count = db.get_referral_count(user.id)

    await context.bot.send_message(
        chat_id=user.id,
        text=(
            "✅ <b>Obuna tasdiqlandi! Xush kelibsiz!</b>\n\n"
            f"👤 <b>{user.full_name}</b>\n"
            f"💰 Balans: <b>{balance:,} so'm</b>\n"
            f"👥 Referrallar: <b>{ref_count} ta</b>\n\n"
            "⬇️ Quyidagi menyudan foydalaning:"
        ),
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )

# ──────────────────────────────────────────────
# ASOSIY MENYU
# ──────────────────────────────────────────────

async def _show_main_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user      = update.effective_user
    user_data = db.get_user(user.id)
    balance   = user_data["balance"] if user_data else 0
    ref_count = db.get_referral_count(user.id)

    await update.message.reply_text(
        f"🏠 <b>ASOSIY MENYU</b>\n\n"
        f"👤 <b>{user.full_name}</b>\n"
        f"💰 Balans: <b>{balance:,} so'm</b>\n"
        f"👥 Referrallar: <b>{ref_count} ta</b>\n\n"
        f"💡 Do'stlaringizni taklif qiling va\n"
        f"<b>{BONUS_PER_REFERRAL:,} so'm</b> ishlang! 🚀",
        reply_markup=main_keyboard(),
        parse_mode="HTML"
    )

# ──────────────────────────────────────────────
# PUL ISHLASH
# ──────────────────────────────────────────────

async def pul_ishlash(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_sub(update, context):
        return
    user      = update.effective_user
    ref_link  = f"https://t.me/{BOT_USERNAME}?start=r{user.id}"
    ref_count = db.get_referral_count(user.id)
    user_data = db.get_user(user.id)
    balance   = user_data["balance"] if user_data else 0

    await update.message.reply_text(
        f"💸 <b>PUL ISHLASH</b>\n\n"
        f"🔗 <b>SIZNING REFERRAL HAVOLANGIZ:</b>\n"
        f"<code>{ref_link}</code>\n\n"
        f"💰 <b>HAR BIR TAKLIF UCHUN {BONUS_PER_REFERRAL:,} so'm</b> olasiz!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Taklif qilganlar: <b>{ref_count} ta</b>\n"
        f"💵 Joriy balans: <b>{balance:,} so'm</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📋 <b>Qanday ishlaydi?</b>\n"
        f"1️⃣ Yuqoridagi havolani nusxalang\n"
        f"2️⃣ Do'stlaringizga yuboring\n"
        f"3️⃣ Do'stingiz kirsa — <b>{BONUS_PER_REFERRAL:,} so'm</b> avtomatik tushadi ✅",
        parse_mode="HTML"
    )

# ──────────────────────────────────────────────
# BALANS
# ──────────────────────────────────────────────

async def balans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_sub(update, context):
        return
    user      = update.effective_user
    user_data = db.get_user(user.id)
    balance   = user_data["balance"] if user_data else 0
    ref_count = db.get_referral_count(user.id)

    await update.message.reply_text(
        f"💰 <b>BALANSINGIZ</b>\n\n"
        f"👤 <b>{user.full_name}</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💵 Joriy balans: <b>{balance:,} so'm</b>\n"
        f"👥 Taklif qilganlar: <b>{ref_count} ta</b>\n"
        f"📈 Jami ishlangan: <b>{ref_count * BONUS_PER_REFERRAL:,} so'm</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💡 Yechish uchun minimal: <b>{MIN_WITHDRAW:,} so'm</b>",
        parse_mode="HTML"
    )

# ──────────────────────────────────────────────
# BONUS OLISH
# ──────────────────────────────────────────────

async def bonus_olish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_sub(update, context):
        return
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📲 MONIX ILOVASINI YUKLASH 👇", url="https://monix.uz")],
    ])
    await update.message.reply_text(
        f"🎁 <b>BONUS OLISH</b>\n\n"
        f"💳 BONUS OLISH UCHUN:\n\n"
        f"1️⃣ <b>MONIX</b> ilovasini yuklab oling\n"
        f"2️⃣ O'zingizga karta oching\n"
        f"3️⃣ Bonusingizni oling! 💯\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👇 Yuklash uchun bosing:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

# ──────────────────────────────────────────────
# KANALLAR
# ──────────────────────────────────────────────

async def monix_kanal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 Monix Kanal — Kirish", url=CHANNEL_LINK)],
    ])
    await update.message.reply_text(
        f"📢 <b>MONIX KANAL</b>\n\n"
        f"Kanalimizda:\n\n"
        f"📌 Bot yangiliklari\n"
        f"💡 Foydali ma'lumotlar\n"
        f"🎁 Maxsus takliflar\n"
        f"📊 Statistikalar\n\n"
        f"👇 Kanalga kirish uchun bosing:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

async def tolovlar_kanal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("💳 To'lovlar — Ko'rish", url=PROOF_CHANNEL_LINK)],
    ])
    await update.message.reply_text(
        f"💳 <b>TO'LOVLAR</b>\n\n"
        f"✅ Bu kanalda barcha amalga oshirilgan\n"
        f"   to'lovlar jamlangan — isbot sifatida\n"
        f"   ko'rishingiz mumkin!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔒 Bot 100% ishonchli va to'lovlar haqiqiy!\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"👇 To'lovlar tarixini ko'rish uchun bosing:",
        reply_markup=keyboard,
        parse_mode="HTML"
    )

# ──────────────────────────────────────────────
# PUL YECHISH
# ──────────────────────────────────────────────

async def pul_yechish_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await require_sub(update, context):
        return ConversationHandler.END
    user      = update.effective_user
    user_data = db.get_user(user.id)
    balance   = user_data["balance"] if user_data else 0

    status = "✅ Yechishingiz mumkin!" if balance >= MIN_WITHDRAW else f"❌ Hali {(MIN_WITHDRAW - balance):,} so'm yetishmaydi"

    await update.message.reply_text(
        f"🗂 <b>PUL YECHISH</b>\n\n"
        f"Assalomu alaykum, <b>{user.full_name}</b>!\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"💰 Balansingiz: <b>{balance:,} so'm</b>\n"
        f"⚠️ Minimal: <b>{MIN_WITHDRAW:,} so'm</b>\n"
        f"📊 Holat: {status}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"💳 <b>Karta raqami yoki telefon raqamingizni yuboring:</b>",
        reply_markup=withdraw_keyboard(),
        parse_mode="HTML"
    )
    return WAITING_CARD


async def pul_yechish_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    user = update.effective_user

    if text == "🚫 Bekor qilish":
        await update.message.reply_text("❌ <b>Bekor qilindi.</b>", reply_markup=main_keyboard(), parse_mode="HTML")
        return ConversationHandler.END

    if text == "✅ Yuborish":
        card      = context.user_data.get("card")
        user_data = db.get_user(user.id)
        balance   = user_data["balance"] if user_data else 0

        if not card:
            await update.message.reply_text("❌ Karta/nomer kiritilmadi. Qaytadan kiriting:")
            return WAITING_CARD

        if balance < MIN_WITHDRAW:
            await update.message.reply_text(
                f"❌ <b>Balansingiz yetarli emas!</b>\n\n"
                f"💰 Balans: <b>{balance:,} so'm</b>\n"
                f"📌 Minimal: <b>{MIN_WITHDRAW:,} so'm</b>\n\n"
                f"💡 Ko'proq do'st taklif qiling!",
                reply_markup=main_keyboard(),
                parse_mode="HTML"
            )
            return ConversationHandler.END

        wid = db.create_withdrawal(user.id, card, balance)

        await update.message.reply_text(
            f"✅ <b>SO'ROVINGIZ ADMINGA YUBORILDI!</b>\n\n"
            f"💳 Karta/Nomer: <code>{card}</code>\n"
            f"💰 Summa: <b>{balance:,} so'm</b>\n\n"
            f"⏱ <b>Pul 24 soat ichida hisobingizga o'tkaziladi!</b>\n\n"
            f"💳 To'lovni kuzatish: {PROOF_CHANNEL_LINK}",
            reply_markup=main_keyboard(),
            parse_mode="HTML"
        )

        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=(
                f"🔔 <b>YANGI YECHISH SO'ROVI #{wid}</b>\n\n"
                f"👤 {user.full_name} (@{user.username or 'yoq'})\n"
                f"🆔 <code>{user.id}</code>\n"
                f"💳 <code>{card}</code>\n"
                f"💰 <b>{balance:,} so'm</b>\n\n"
                f"✅ /approve_{wid}\n"
                f"❌ /reject_{wid}"
            ),
            parse_mode="HTML"
        )
        context.user_data.clear()
        return ConversationHandler.END

    # Karta saqlash
    context.user_data["card"] = text
    await update.message.reply_text(
        f"✅ <b>Qabul qilindi:</b> <code>{text}</code>\n\n"
        f"To'g'ri bo'lsa «✅ Yuborish» bosing.\n"
        f"O'zgartirmoqchi bo'lsangiz qaytadan yuboring.",
        reply_markup=withdraw_keyboard(),
        parse_mode="HTML"
    )
    return WAITING_CARD

# ──────────────────────────────────────────────
# ADMIN
# ──────────────────────────────────────────────

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    if user.id != ADMIN_ID:
        await update.message.reply_text(f"👤 <b>Admin:</b> {ADMIN_USERNAME}", parse_mode="HTML")
        return
    stats = db.get_stats()
    await update.message.reply_text(
        f"⚙️ <b>ADMIN PANEL</b>\n\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"👥 Foydalanuvchilar: <b>{stats['total_users']}</b>\n"
        f"🔗 Referrallar: <b>{stats['total_referrals']}</b>\n"
        f"💰 To'langan: <b>{stats['total_bonuses']:,} so'm</b>\n"
        f"📥 Kutilmoqda: <b>{stats['pending_withdrawals']} ta</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━\n\n"
        f"/withdrawals — So'rovlar\n"
        f"/broadcast Matn — Hammaga xabar\n"
        f"/users — Foydalanuvchilar",
        parse_mode="HTML"
    )


async def withdrawals_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    items = db.get_pending_withdrawals()
    if not items:
        await update.message.reply_text("✅ Kutilayotgan so'rovlar yo'q.")
        return
    text = f"📥 <b>So'rovlar ({len(items)} ta):</b>\n\n"
    for w in items:
        text += (
            f"🆔 <b>#{w['id']}</b> | {w['name']}\n"
            f"💳 <code>{w['card']}</code>\n"
            f"💰 <b>{w['amount']:,} so'm</b>\n"
            f"✅ /approve_{w['id']}   ❌ /reject_{w['id']}\n"
            f"──────────────────\n"
        )
    await update.message.reply_text(text, parse_mode="HTML")


async def approve_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        wid = int(update.message.text.split("_")[1])
        w   = db.get_withdrawal(wid)
        if not w or w["status"] != "pending":
            await update.message.reply_text("❌ Topilmadi yoki ko'rib chiqilgan.")
            return
        db.approve_withdrawal(wid)
        db.deduct_balance(w["user_id"], w["amount"])
        await update.message.reply_text(f"✅ <b>#{wid} tasdiqlandi!</b>", parse_mode="HTML")
        await context.bot.send_message(
            chat_id=w["user_id"],
            text=(
                f"🎉 <b>TO'LOVINGIZ AMALGA OSHIRILDI!</b>\n\n"
                f"💰 <b>{w['amount']:,} so'm</b> kartangizga o'tkazildi!\n"
                f"💳 <code>{w['card']}</code>\n\n"
                f"✅ Isbot: {PROOF_CHANNEL_LINK}\n\n"
                f"Rahmat! 🙏"
            ),
            parse_mode="HTML"
        )
        try:
            chat = await context.bot.get_chat(w["user_id"])
            await context.bot.send_message(
                chat_id=PROOF_CHANNEL,
                text=(
                    f"✅ <b>TO'LOV AMALGA OSHIRILDI!</b>\n\n"
                    f"👤 <b>{chat.full_name}</b>\n"
                    f"💰 <b>{w['amount']:,} so'm</b>\n"
                    f"💳 <code>{w['card']}</code>\n\n"
                    f"🤖 @{BOT_USERNAME}"
                ),
                parse_mode="HTML"
            )
        except Exception:
            pass
    except Exception as e:
        await update.message.reply_text(f"Xatolik: {e}")


async def reject_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        wid = int(update.message.text.split("_")[1])
        w   = db.get_withdrawal(wid)
        if not w:
            await update.message.reply_text("❌ Topilmadi.")
            return
        db.reject_withdrawal(wid)
        await update.message.reply_text(f"❌ <b>#{wid} rad etildi.</b>", parse_mode="HTML")
        await context.bot.send_message(
            chat_id=w["user_id"],
            text=(
                f"❌ <b>SO'ROVINGIZ RAD ETILDI</b>\n\n"
                f"Muammo bo'lsa: {ADMIN_USERNAME}"
            ),
            parse_mode="HTML"
        )
    except Exception as e:
        await update.message.reply_text(f"Xatolik: {e}")


async def broadcast_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Ishlatish: /broadcast Xabar matni")
        return
    msg   = " ".join(context.args)
    users = db.get_all_users()
    sent  = 0
    for u in users:
        try:
            await context.bot.send_message(chat_id=u["user_id"], text=msg, parse_mode="HTML")
            sent += 1
        except Exception:
            pass
    await update.message.reply_text(f"✅ <b>{sent}</b> foydalanuvchiga yuborildi.", parse_mode="HTML")


async def users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    stats = db.get_stats()
    await update.message.reply_text(f"👥 <b>Jami: {stats['total_users']} foydalanuvchi</b>", parse_mode="HTML")

# ──────────────────────────────────────────────
# TEXT HANDLER
# ──────────────────────────────────────────────

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text == "💸 PUL ISHLASH 💸":
        await pul_ishlash(update, context)
    elif text == "💰 BALANS":
        await balans(update, context)
    elif text == "✅ BONUS OLISH":
        await bonus_olish(update, context)
    elif text == "📢 Monix Kanal":
        await monix_kanal(update, context)
    elif text == "💳 To'lovlar":
        await tolovlar_kanal(update, context)
    elif text == "👤 ADMIN":
        await admin_panel(update, context)
    elif text.startswith("/approve_"):
        await approve_cmd(update, context)
    elif text.startswith("/reject_"):
        await reject_cmd(update, context)

# ──────────────────────────────────────────────
# MAIN
# ──────────────────────────────────────────────

def main():
    app = Application.builder().token(BOT_TOKEN).updater(None).build()

    withdraw_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^🗂 PUL YECHISH$"), pul_yechish_start)],
        states={WAITING_CARD: [MessageHandler(filters.TEXT & ~filters.COMMAND, pul_yechish_input)]},
        fallbacks=[CommandHandler("start", start)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("withdrawals", withdrawals_list))
    app.add_handler(CommandHandler("broadcast", broadcast_cmd))
    app.add_handler(CommandHandler("users", users_cmd))
    app.add_handler(CallbackQueryHandler(check_sub_callback, pattern="^check_sub$"))
    app.add_handler(withdraw_conv)
    app.add_handler(MessageHandler(filters.Regex(r"^/approve_\d+$"), approve_cmd))
    app.add_handler(MessageHandler(filters.Regex(r"^/reject_\d+$"), reject_cmd))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("✅ MONIX BOT ishga tushdi!")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
