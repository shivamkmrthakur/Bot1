#!/usr/bin/env python3
# bot.py

import os
import time
import hmac
import hashlib
import base64
import psycopg2
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# ----------------- CONFIG -----------------
TOKEN = "8293205720:AAGPGvxkXJmy_-zj0rYSjFruKTba-1bVit8"
SOURCE_CHANNEL = -1002934836217
JOIN_CHANNELS = ["@instahubackup", "@instahubackup2"]

SECRET_KEY = b"G7r9Xm2qT5vB8zN4pL0sQwE6yH1uR3cKfVb9ZaP2"
REDEEM_WINDOW_SECONDS = 3 * 60 * 60

DATABASE_URL = "postgresql://postgres:ldmbL0jjXKdZ83X6J8aP@containers-us-west-57.railway.app:6904/railway"

# ---------------- DB HELPERS ----------------
def init_db():
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS verified_users (
            user_id BIGINT PRIMARY KEY,
            expiry BIGINT
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

def save_user(user_id: int, expiry: int):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO verified_users (user_id, expiry)
        VALUES (%s, %s)
        ON CONFLICT (user_id) DO UPDATE SET expiry = EXCLUDED.expiry
    """, (user_id, expiry))
    conn.commit()
    cur.close()
    conn.close()

def get_user_expiry(user_id: int):
    conn = psycopg2.connect(DATABASE_URL)
    cur = conn.cursor()
    cur.execute("SELECT expiry FROM verified_users WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row[0] if row else None

# ---------------- VERIFY HELPERS ----------------
def set_verified_for_seconds(user_id: int, seconds: int):
    now = time.time()
    current_expiry = get_user_expiry(user_id) or 0
    base = max(now, current_expiry)
    new_expiry = int(base + seconds)
    save_user(user_id, new_expiry)

def set_verified_24h(user_id: int):
    set_verified_for_seconds(user_id, 24 * 60 * 60)

def is_verified(user_id: int):
    expiry = get_user_expiry(user_id)
    if expiry and time.time() < expiry:
        return True
    return False

# ---------------- legacy validate ----------------
SIG_LEN = 12

def validate_code_anyuser(code: str) -> bool:
    try:
        ts_str, sig = code.split("_", 1)
        ts = int(ts_str)
    except Exception:
        return False
    if abs(time.time() - ts) > 600:
        return False
    msg = ts_str.encode()
    expected = hmac.new(SECRET_KEY, msg, hashlib.sha256).hexdigest()[:SIG_LEN]
    return hmac.compare_digest(expected, sig)

# ---------------- premium token helpers ----------------
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

# ---------------- HANDLERS ----------------
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if is_verified(user_id):
        await update.message.reply_text("✅ You are already verified!")
    else:
        buttons = [[InlineKeyboardButton("✅ Verify Now", callback_data="check_join")]]
        await update.message.reply_text(
            "🚀 Please join the required channels to get verified.",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

async def verified_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    expiry = get_user_expiry(user_id)
    if expiry and time.time() < expiry:
        left = int(expiry - time.time())
        hours = left // 3600
        mins = (left % 3600) // 60
        await update.message.reply_text(f"✅ Verified! Time left: {hours}h {mins}m")
    else:
        await update.message.reply_text("❌ Not verified!")

async def redeem_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not context.args:
        await update.message.reply_text("⚠️ Usage: /redeem <token>")
        return
    token = context.args[0]
    ok, msg, seconds = validate_premium_token_for_user(token, user_id)
    if not ok:
        await update.message.reply_text(f"❌ Invalid: {msg}")
        return
    set_verified_for_seconds(user_id, seconds)
    await update.message.reply_text(f"✅ Premium activated for {seconds//3600} hours!")

async def join_check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    set_verified_24h(user_id)
    await query.edit_message_text("🎉 Verified for 24h!")

async def remove_ads_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Ads removed for you!")

async def close_ads_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer("Closed ads.")

# ---------------- MAIN ----------------
def main():
    init_db()
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
