# file: direct_forward_bot.py
import os
import re
import logging
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    CallbackQueryHandler, ContextTypes, filters
)
from telegram.error import Forbidden, TimedOut, TelegramError

# ---------------------- CONFIG ----------------------
load_dotenv()  # Load BOT_TOKEN from .env file

BOT_TOKEN = os.getenv("BOT_TOKEN")  # <- Securely loaded from environment
BOT_OWNER_ID = int(os.getenv("BOT_OWNER_ID", "0"))  # can set in .env
ADMIN_CHAT_ID = int(os.getenv("ADMIN_CHAT_ID", "0"))  # can set in .env

# Default SLA (in hours). Can be changed at runtime by owner with /setdeadline <hours>.
DEFAULT_DEADLINE_HOURS = 12

REQUEST_FORMAT_HELP = (
    "Please use this format:\n\n"
    "#Request\n"
    "Name: <Movie/Series Title>\n"
    "Year: <Release Year>\n"
    "Quality: <e.g., 1080p, 720p>\n"
    "Language: <e.g., English, Hindi, Dual Audio>\n"
)

# ---------------------- LOGGING ---------------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger("direct-forward-bot")

# ---------------------- HELPERS ---------------------
def parse_request(text: str):
    """
    Extract Name, Year, Quality, Language from free text (flexible).
    Returns tuple (name, year, quality, language).
    """
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    content = "\n".join(lines)

    def find(key: str):
        m = re.search(rf"(?im)^(?:{key})\s*[:=]?\s*(.+)$", content)
        return m.group(1).strip() if m else None

    name = find("Name|Title")
    year = find("Year")
    quality = find("Quality")
    language = find("Language|Audio")

    # sanitize year
    if year and not re.match(r"^\d{4}$", year):
        year = None
    return name, year, quality, language

def looks_like_request(text: str) -> bool:
    return bool(re.search(r"(?i)(^|\s)#?\s*request(\b|\s)", text or ""))

def eta_string(hours: int) -> str:
    now_utc = datetime.now(timezone.utc)
    deadline = now_utc + timedelta(hours=hours)
    return f"within {hours} hour(s) (by {deadline.strftime('%Y-%m-%d %H:%M UTC')})"

def admin_keyboard(user_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[
        InlineKeyboardButton("✅ Mark done", callback_data=f"done:{user_id}"),
        InlineKeyboardButton("❌ Reject", callback_data=f"reject:{user_id}"),
    ]])

def is_owner(user_id: int) -> bool:
    return user_id == BOT_OWNER_ID

# ---------------------- HANDLERS --------------------
async def cmd_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hours = context.bot_data.get("deadline_hours", DEFAULT_DEADLINE_HOURS)
    msg = (
        "🎬 Welcome to the Movies & Series Request Bot!\n\n"
        "Send a request in this format:\n\n"
        f"{REQUEST_FORMAT_HELP}\n"
        f"⏳ Current ETA: requests are typically fulfilled {eta_string(hours)}."
    )
    await update.message.reply_text(msg)

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    hours = context.bot_data.get("deadline_hours", DEFAULT_DEADLINE_HOURS)
    text = (
        "🆘 Help\n\n"
        "• Send your request starting with #Request (or the word Request) and include details.\n"
        "• Example:\n"
        "#Request\nName: Example Movie\nYear: 2024\nQuality: 1080p\nLanguage: Hindi\n\n"
        f"⏳ ETA: {eta_string(hours)}\n\n"
        "Owner only:\n"
        "• /setdeadline <hours> — change the ETA for future requests (not persisted).\n"
    )
    await update.message.reply_text(text)

async def cmd_setdeadline(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_owner(update.effective_user.id):
        return await update.message.reply_text("❌ Owner only.")
    if not context.args:
        return await update.message.reply_text("Usage: /setdeadline <hours>")
    try:
        hours = int(context.args[0])
        if hours <= 0 or hours > 168:
            return await update.message.reply_text("Choose a value between 1 and 168 hours.")
    except ValueError:
        return await update.message.reply_text("Hours must be an integer.")
    context.bot_data["deadline_hours"] = hours
    await update.message.reply_text(f"✅ Deadline updated. New ETA: {eta_string(hours)}")

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text

    if not looks_like_request(text):
        return  # ignore non-request messages

    # Strip the trigger word (#Request / request)
    cleaned = re.sub(r"(?i)#?\s*request", "", text).strip()
    name, year, quality, language = parse_request(cleaned)

    hours = context.bot_data.get("deadline_hours", DEFAULT_DEADLINE_HOURS)
    eta = eta_string(hours)

    # 1) Acknowledge to the USER
    user_reply = [
        "✅ Your request has been received!",
        f"⏳ We aim to fulfill it {eta}.",
        "",
        "Here’s what I understood:",
        f"• Name: {name or '-'}",
        f"• Year: {year or '-'}",
        f"• Quality: {quality or '-'}",
        f"• Language: {language or '-'}",
    ]
    if not (name and year and quality and language):
        user_reply.append(
            "\nℹ️ Tip: Include all fields for faster processing:\n" + REQUEST_FORMAT_HELP
        )
    await update.message.reply_text("\n".join(user_reply))

    # 2) Forward to the ADMIN CHANNEL
    now_utc = datetime.now(timezone.utc)
    deadline = now_utc + timedelta(hours=hours)
    u = update.effective_user

    admin_text = (
        "🆕 New Request\n"
        f"From: @{u.username or u.id} (id: {u.id})\n"
        f"Name: {name or '-'}\n"
        f"Year: {year or '-'}\n"
        f"Quality: {quality or '-'}\n"
        f"Language: {language or '-'}\n\n"
        f"Raw:\n{text[:1000]}\n\n"
        f"⏳ Deadline: {deadline.strftime('%Y-%m-%d %H:%M:%S UTC')}  (in {hours}h)"
    )

    try:
        await context.bot.send_message(
            chat_id=ADMIN_CHAT_ID,
            text=admin_text,
            reply_markup=admin_keyboard(u.id),
            disable_web_page_preview=True,
        )
    except Forbidden:
        logger.error("Admin chat unauthorized or bot blocked.")
    except TimedOut:
        logger.error("Telegram API timeout when sending to admin chat.")
    except TelegramError as e:
        logger.error(f"Telegram error while sending to admin chat: {e}")

async def cb_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    if not q or not q.data:
        return
    await q.answer()

    actor = q.from_user
    if not is_owner(actor.id):
        await q.message.reply_text("❌ Only the owner can perform this action.")
        return

    try:
        action, user_id_str = q.data.split(":", 1)
        target_uid = int(user_id_str)
    except Exception:
        await q.message.reply_text("⚠️ Invalid action payload.")
        return

    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")

    if action == "done":
        try:
            await context.bot.send_message(
                chat_id=target_uid,
                text="🎉 Update: Your request has been fulfilled. Enjoy!"
            )
        except Exception as e:
            logger.info(f"Could not notify user {target_uid}: {e}")

        try:
            await q.edit_message_text(q.message.text + f"\n\n✅ Marked done by @{actor.username or actor.id} at {now_utc}")
        except Exception:
            await q.message.reply_text(f"✅ Marked done by @{actor.username or actor.id} at {now_utc}")

    elif action == "reject":
        try:
            await context.bot.send_message(
                chat_id=target_uid,
                text="😔 Update: Your request was rejected."
            )
        except Exception as e:
            logger.info(f"Could not notify user {target_uid}: {e}")

        try:
            await q.edit_message_text(q.message.text + f"\n\n❌ Rejected by @{actor.username or actor.id} at {now_utc}")
        except Exception:
            await q.message.reply_text(f"❌ Rejected by @{actor.username or actor.id} at {now_utc}")

# ---------------------- MAIN ----------------------
async def on_startup(app):
    if "deadline_hours" not in app.bot_data:
        app.bot_data["deadline_hours"] = DEFAULT_DEADLINE_HOURS
    logger.info("Bot initialized. Admin chat: %s, Owner: %s", ADMIN_CHAT_ID, BOT_OWNER_ID)

def main():
    if not BOT_TOKEN:
        raise SystemExit("❌ BOT_TOKEN not set in environment.")
    application = (
        ApplicationBuilder()
        .token(BOT_TOKEN)
        .post_init(on_startup)
        .build()
    )

    application.add_handler(CommandHandler("start", cmd_start))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("setdeadline", cmd_setdeadline))
    application.add_handler(CallbackQueryHandler(cb_admin))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))

    logger.info("Bot is running...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
