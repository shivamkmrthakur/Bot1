#!/usr/bin/env python3
# bot.py

import os
import json
import time
import hmac
import hashlib
import base64
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# ----------------- CONFIG -----------------
TOKEN = "8409312798:AAF9aVNMdSynS5ndEOiyKe8Bc2NDe3dNk1I"
SOURCE_CHANNEL = -1002934836217
JOIN_CHANNELS = ["@instahubackup", "@instahubackup2"]

VERIFY_FILE = "verified_users.json"
USERS_FILE = "users.json"

SECRET_KEY = b"G7r9Xm2qT5vB8zN4pL0sQwE6yH1uR3cKfVb9ZaP2"
REDEEM_WINDOW_SECONDS = 3 * 60 * 60

ADMIN_ID = 7994709010  # your Telegram ID

# ---------------- VERIFY HELPERS -----------------
def load_verified():
    if os.path.exists(VERIFY_FILE):
        try:
            with open(VERIFY_FILE, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_verified(data):
    with open(VERIFY_FILE, "w") as f:
        json.dump(data, f)

def set_verified_for_seconds(user_id: int, seconds: int):
    verified = load_verified()
    now = time.time()
    current_expiry = verified.get(str(user_id), 0)
    base = max(now, current_expiry)
    verified[str(user_id)] = base + seconds
    save_verified(verified)

def set_verified_24h(user_id: int):
    set_verified_for_seconds(user_id, 24 * 60 * 60)

def is_verified(user_id: int):
    verified = load_verified()
    key = str(user_id)
    if key in verified:
        if time.time() < verified[key]:
            return True
        del verified[key]
        save_verified(verified)
    return False

def get_expiry_time(user_id: int):
    verified = load_verified()
    key = str(user_id)
    if key not in verified:
        return 0
    expiry = verified[key]
    remaining = expiry - time.time()
    return max(0, int(remaining))

# ---------------- USERS TRACKING ----------------
def load_users():
    if os.path.exists(USERS_FILE):
        try:
            with open(USERS_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_users(users):
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

def add_user(user_id: int):
    users = load_users()
    if user_id not in users:
        users.append(user_id)
        save_users(users)

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
        [InlineKeyboardButton("🚫 Remove Ads / Get Premium", callback_data="remove_ads")]
    ])

# ---------------- COMMANDS ----------------
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.first_name or "User"
    text = (update.message.text or "").strip()

    add_user(user_id)  # Track user

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
            await update.message.reply_text("✅ You’re already verified!\n\nGo to InstaHub, choose a video, and I’ll send it here for you.")
        else:
            await update.message.reply_text(
                f"👋 Welcome {username}!\n\n"
                "This bot helps you get InstaHub videos.\n\n"
                "🔒 Please verify yourself to unlock 24-hour access.",
                reply_markup=verify_menu_kb()
            )
        return

# ---------------- NEW FEATURE: EXPIRY ----------------
async def expiry_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    remaining = get_expiry_time(user_id)

    if remaining <= 0:
        await update.message.reply_text("⏳ You don’t have an active verification right now.\n\nUse /start to verify.")
        return

    days = remaining // (24*3600)
    hours = (remaining % (24*3600)) // 3600
    minutes = (remaining % 3600) // 60

    msg = "⏳ Your verification is active!\n\n"
    if days > 0:
        msg += f"✅ Time left: {days} day(s), {hours} hour(s), {minutes} min"
    elif hours > 0:
        msg += f"✅ Time left: {hours} hour(s), {minutes} min"
    else:
        msg += f"✅ Time left: {minutes} min"

    await update.message.reply_text(msg)

# ---------------- NEW FEATURE: ADMIN DASHBOARD ----------------
async def dashboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        await update.message.reply_text("❌ You are not authorized to view this.")
        return

    users = load_users()
    verified = load_verified()

    total_users = len(users)
    verified_now = sum(1 for uid, expiry in verified.items() if expiry > time.time())
    premium_users = sum(1 for uid, expiry in verified.items() if expiry - time.time() > 24*3600)

    msg = (
        "📊 **Bot Dashboard**\n\n"
        f"👥 Total Users: {total_users}\n"
        f"✅ Verified Users (active): {verified_now}\n"
        f"🌟 Premium Users: {premium_users}"
    )

    await update.message.reply_text(msg, parse_mode="Markdown")

# ---------------- MAIN ----------------
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("expiry", expiry_handler))
    app.add_handler(CommandHandler("dashboard", dashboard_handler))
    # keep your other handlers (verified, redeem, callbacks, etc.)

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
