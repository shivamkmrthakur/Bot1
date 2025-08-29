#!/usr/bin/env python3
# bot.py

import time
import hmac
import hashlib
import base64
import psycopg2
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# ----------------- CONFIG -----------------
TOKEN = "8293205720:AAGPGvxkXJmy_-zj0rYSjFruKTba-1bVit8"
SOURCE_CHANNEL = -1002934836217   # वीडियो source channel
JOIN_CHANNELS = ["@instahubackup", "@instahubackup2"]

SECRET_KEY = b"G7r9Xm2qT5vB8zN4pL0sQwE6yH1uR3cKfVb9ZaP2"
REDEEM_WINDOW_SECONDS = 3 * 60 * 60   # 3h redeem window

# ----------------- DATABASE -----------------
DB_URL = "postgresql://postgres:dxQLpasirfqfmuBNoWCUomgQmIIGjPmK@yamabiko.proxy.rlwy.net:55695/railway"

def init_db():
    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("""
            CREATE TABLE IF NOT EXISTS verified (
                user_id TEXT PRIMARY KEY,
                expiry REAL
            )
            """)
            conn.commit()

init_db()

def set_verified_for_seconds(user_id: int, seconds: int):
    now = time.time()
    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT expiry FROM verified WHERE user_id=%s", (str(user_id),))
            row = cur.fetchone()
            current_expiry = row[0] if row else 0
            base = max(now, current_expiry)
            expiry = base + seconds
            cur.execute("""
                INSERT INTO verified (user_id, expiry) 
                VALUES (%s, %s)
                ON CONFLICT (user_id) DO UPDATE SET expiry = %s
            """, (str(user_id), expiry, expiry))
            conn.commit()

def set_verified_24h(user_id: int):
    set_verified_for_seconds(user_id, 24 * 3600)

def is_verified(user_id: int):
    with psycopg2.connect(DB_URL) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT expiry FROM verified WHERE user_id=%s", (str(user_id),))
            row = cur.fetchone()
            if row and time.time() < row[0]:
                return True
    return False

# ---------------- TOKEN SYSTEM ----------------
SIG_LEN = 12

def validate_code_anyuser(code: str) -> bool:
    try:
        ts_str, sig = code.split("_", 1)
        ts = int(ts_str)
    except Exception:
        return False
    if abs(time.time() - ts) > 600:  # 10 min expiry
        return False
    msg = ts_str.encode()
    expected = hmac.new(SECRET_KEY, msg, hashlib.sha256).hexdigest()[:SIG_LEN]
    return hmac.compare_digest(expected, sig)

def build_premium_token_payload(user_id: int, days: int, hours: int, ts: int) -> str:
    return f"{ts}|{user_id}|{days}|{hours}"

def sign_payload_hex(payload: str) -> str:
    return hmac.new(SECRET_KEY, payload.encode(), hashlib.sha256).hexdigest()

def encode_premium_token(payload: str, hex_sig: str) -> str:
    combined = f"{payload}|{hex_sig}"
    return base64.b64encode(combined.encode()).decode()

def decode_premium_token(token_b64: str):
    try:
        raw = base64.b64decode(token_b64).decode()
    except Exception:
        return False, "Token is not valid base64.", None, None
    if "|" not in raw:
        return False, "Token payload malformed.", None, None
    parts = raw.rsplit("|", 1)
    if len(parts) != 2:
        return False, "Token malformed.", None, None
    payload, hex_sig = parts
    if not hex_sig or len(hex_sig) < 10:
        return False, "Invalid signature part.", None, None
    return True, "OK", payload, hex_sig

def validate_premium_token_for_user(token_b64: str, actual_user_id: int):
    ok, msg, payload, hex_sig = decode_premium_token(token_b64)
    if not ok:
        return False, msg, 0

    parts = payload.split("|")
    if len(parts) != 4:
        return False, "Invalid payload fields.", 0
    try:
        ts = int(parts[0])
        uid = int(parts[1])
        days = int(parts[2])
        hours = int(parts[3])
    except Exception:
        return False, "Payload contains invalid integers.", 0

    if uid != actual_user_id:
        return False, "Token is not for this user.", 0

    if time.time() - ts > REDEEM_WINDOW_SECONDS:
        return False, "Token redeem window (3h) has passed.", 0

    expected_hex = sign_payload_hex(payload)
    if not hmac.compare_digest(expected_hex, hex_sig):
        return False, "Signature mismatch.", 0

    grant_seconds = days * 24 * 3600 + hours * 3600
    if grant_seconds <= 0:
        return False, "Duration must be positive.", 0

    return True, "OK", grant_seconds

# ---------------- HELPERS ----------------
async def check_user_in_channels(bot, user_id):
    for channel in JOIN_CHANNELS:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception:
            return False
    return True

def verify_menu_kb():
    return InlineKeyboardMarkup([
        [
            InlineKeyboardButton("✅ Verify (Open Site)", url="https://adrinolinks.com/NmL2Y"),
            InlineKeyboardButton("ℹ️ How to Verify?", url="https://t.me/howtoverifyyourtoken")
        ],
        [InlineKeyboardButton("🚫 Remove Ads / Any Doubt", callback_data="remove_ads")]
    ])

# ---------------- HANDLERS ----------------
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id
    username = update.effective_user.first_name or "User"

    # fresh start
    if text == "/start":
        if not await check_user_in_channels(context.bot, user_id):
            keyboard = [[InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{ch.replace('@','')}")] for ch in JOIN_CHANNELS]
            keyboard.append([InlineKeyboardButton("🔄 I Joined, Retry", callback_data="check_join")])
            await update.message.reply_text(
                f"👋 Hi {username}!\n\n"
                "To continue using this bot, please join all the required channels first.\n\n"
                "👉 Once done, tap **Retry** below.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        if is_verified(user_id):
            await update.message.reply_text(
                "✅ You’re already verified!\n\nGo to [@Instaa_hubb](https://t.me/instaa_hubb), choose a video, and I’ll send it here for you.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"👋 Welcome {username}!\n\n"
                "This bot helps you get videos from [@Instaa_hubb](https://t.me/instaa_hubb).\n\n"
                "🔒 Please verify yourself to unlock 24-hour access.",
                reply_markup=verify_menu_kb(),
                parse_mode="Markdown"
            )
        return

    # payload after /start
    if " " in text:
        payload = text.split(" ", 1)[1].strip()
    else:
        payload = text[len("/start"):].strip()

    if payload.startswith("verified="):
        code = payload.replace("verified=", "", 1).strip()
        if validate_code_anyuser(code):
            set_verified_24h(user_id)
            await update.message.reply_text("🎉 Verification successful! You’re now verified for 24 hours.")
        else:
            await update.message.reply_text("❌ Invalid or expired verification code.")
        return

    if payload.isdigit():
        video_id = int(payload)
        if not await check_user_in_channels(context.bot, user_id):
            await update.message.reply_text("❌ Please join required channels first.")
            return
        if is_verified(user_id):
            try:
                await context.bot.copy_message(
                    chat_id=user_id,
                    from_chat_id=SOURCE_CHANNEL,
                    message_id=video_id,
                    protect_content=True
                )
                await update.message.reply_text("✅ Here’s your requested video.")
            except Exception as e:
                await update.message.reply_text(f"⚠️ Error: {e}")
        else:
            await update.message.reply_text("🔒 Please verify first.", reply_markup=verify_menu_kb())
    else:
        await update.message.reply_text("❌ Invalid command.\n\n👉 Use bot from [@Instaa_hubb](https://t.me/instaa_hubb).", parse_mode="Markdown")

async def verified_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    set_verified_24h(user_id)
    await update.message.reply_text("🎉 Success! You’re verified for 24h.")

async def redeem_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await update.message.reply_text("⚠️ Usage: `/redeem <TOKEN>`", parse_mode="Markdown")
        return
    token = parts[1].strip()
    ok, msg, grant_seconds = validate_premium_token_for_user(token, update.effective_user.id)
    if ok:
        set_verified_for_seconds(update.effective_user.id, grant_seconds)
        await update.message.reply_text("🎉 Premium redeemed successfully!")
    else:
        await update.message.reply_text(f"❌ {msg}")

async def join_check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    if await check_user_in_channels(context.bot, user_id):
        await query.message.edit_text("✅ Thanks! You joined all channels. Use /start again.")
    else:
        await query.answer("❌ Still missing channel join!", show_alert=True)

async def remove_ads_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.reply_text("✨ Premium removes ads.\n💵 Pay via UPI: `roshanbot@fam`")

async def close_ads_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.callback_query.message.delete()

# ---------------- MAIN ----------------
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("verified", verified_handler))
    app.add_handler(CommandHandler("redeem", redeem_handler))
    app.add_handler(CallbackQueryHandler(join_check_callback, pattern="check_join"))
    app.add_handler(CallbackQueryHandler(remove_ads_callback, pattern="remove_ads"))
    app.add_handler(CallbackQueryHandler(close_ads_callback, pattern="close_ads"))

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
