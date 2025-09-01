#!/usr/bin/env python3
# bot.py

import os
import json
import time
import hmac
import hashlib
import base64
import asyncio
import asyncpg
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# ----------------- CONFIG -----------------
TOKEN = "8409312798:AAErfYLxziXCDEtZWGHj8JFStG1_Vn2uNWg"
SOURCE_CHANNEL = -1002934836217
JOIN_CHANNELS = ["@instahubackup", "@instahubackup2"]

SECRET_KEY = b"G7r9Xm2qT5vB8zN4pL0sQwE6yH1uR3cKfVb9ZaP2"
REDEEM_WINDOW_SECONDS = 3 * 60 * 60

DB_URL = "postgresql://postgres:dxQLpasirfqfmuBNoWCUomgQmIIGjPmK@yamabiko.proxy.rlwy.net:55695/railway"

# ---------------- DB INIT ----------------
async def init_db():
    conn = await asyncpg.connect(DB_URL)
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS users (
        user_id BIGINT PRIMARY KEY,
        expiry DOUBLE PRECISION
    );
    """)
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS token_usage (
        token TEXT PRIMARY KEY,
        count INTEGER DEFAULT 0
    );
    """)
    await conn.execute("""
    CREATE TABLE IF NOT EXISTS sent_messages (
        chat_id BIGINT,
        message_id BIGINT,
        delete_after DOUBLE PRECISION
    );
    """)
    await conn.close()

# ---------------- DB HELPERS ----------------
async def set_verified_for_seconds(user_id: int, seconds: int):
    conn = await asyncpg.connect(DB_URL)
    now = time.time()
    expiry = now + seconds
    await conn.execute("""
        INSERT INTO users (user_id, expiry)
        VALUES ($1, $2)
        ON CONFLICT (user_id) DO UPDATE SET expiry = EXCLUDED.expiry
    """, user_id, expiry)
    await conn.close()

async def set_verified_24h(user_id: int):
    await set_verified_for_seconds(user_id, 24 * 3600)

async def is_verified(user_id: int):
    conn = await asyncpg.connect(DB_URL)
    row = await conn.fetchrow("SELECT expiry FROM users WHERE user_id=$1", user_id)
    await conn.close()
    if row and time.time() < row["expiry"]:
        return True
    return False

async def get_token_usage(token: str):
    conn = await asyncpg.connect(DB_URL)
    row = await conn.fetchrow("SELECT count FROM token_usage WHERE token=$1", token)
    await conn.close()
    return row["count"] if row else 0

async def increment_token_usage(token: str):
    conn = await asyncpg.connect(DB_URL)
    await conn.execute("""
        INSERT INTO token_usage (token, count)
        VALUES ($1, 1)
        ON CONFLICT (token) DO UPDATE SET count = token_usage.count + 1
    """, token)
    await conn.close()

async def add_sent_message(chat_id, message_id, delete_after):
    conn = await asyncpg.connect(DB_URL)
    await conn.execute("INSERT INTO sent_messages (chat_id, message_id, delete_after) VALUES ($1,$2,$3)",
                       chat_id, message_id, delete_after)
    await conn.close()

async def load_sent_messages():
    conn = await asyncpg.connect(DB_URL)
    rows = await conn.fetch("SELECT chat_id, message_id, delete_after FROM sent_messages")
    await conn.close()
    return [dict(r) for r in rows]

async def delete_sent_message(chat_id, message_id):
    conn = await asyncpg.connect(DB_URL)
    await conn.execute("DELETE FROM sent_messages WHERE chat_id=$1 AND message_id=$2", chat_id, message_id)
    await conn.close()

# ---------------- NEW: hatched short-token system ----------------
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

def simple_decode(token: str) -> str:
    num = 0
    for ch in token:
        if ch not in ALPHABET:
            raise ValueError("Invalid character in token")
        num = num * len(ALPHABET) + ALPHABET.index(ch)
    if num == 0:
        return ""
    raw = num.to_bytes((num.bit_length() + 7) // 8, "big")
    return raw.decode()

def validate_limit_token(token_str: str):
    try:
        raw = simple_decode(token_str)
    except Exception:
        return False, "❌ Invalid token or decode error.", 0, 0, ""

    parts = raw.split("|")
    if len(parts) != 4:
        return False, "❌ Invalid token format.", 0, 0, ""
    ddmmyy, limit_s, days_s, hours_s = parts
    try:
        limit = int(limit_s)
        days = int(days_s)
        hours = int(hours_s)
    except Exception:
        return False, "❌ Invalid numeric values in token.", 0, 0, ""

    today = time.strftime("%d%m%y")
    if ddmmyy != today:
        return False, "❌ Token expired or invalid date.", 0, 0, ""

    grant_seconds = days * 24 * 3600 + hours * 3600
    if grant_seconds <= 0:
        return False, "❌ Duration must be positive.", 0, 0, ""

    return True, "OK", grant_seconds, limit, raw

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

# ---------------- SENT MESSAGES AUTO DELETE ----------------
async def auto_delete_task(app):
    while True:
        now = time.time()
        messages = await load_sent_messages()

        for entry in messages:
            if now >= entry["delete_after"]:
                try:
                    await app.bot.delete_message(entry["chat_id"], entry["message_id"])
                except Exception:
                    pass
                await delete_sent_message(entry["chat_id"], entry["message_id"])

        await asyncio.sleep(300)

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

    if text == "/start":
        if not await check_user_in_channels(context.bot, user_id):
            keyboard = [[InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{ch.replace('@','')}")] for ch in JOIN_CHANNELS]
            keyboard.append([InlineKeyboardButton("🔄 I Joined, Retry", callback_data="check_join")])
            await update.message.reply_text(
                f"👋 Hi {username}!\n\nJoin required channels then tap Retry.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        if await is_verified(user_id):
            await update.message.reply_text(
                "✅ You’re already verified!\n\nGo to [@Instaa_hubb](https://t.me/instaa_hubb).",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"👋 Welcome {username}!\n\nPlease verify to unlock 24h access.",
                reply_markup=verify_menu_kb(),
                parse_mode="Markdown"
            )
        return

    # Handle payload
    if " " in text:
        payload = text.split(" ", 1)[1].strip()
    else:
        payload = text[len("/start"):].strip()

    # ✅ NEW: Handle hatched multi-user tokens
    if payload.startswith("token="):
        code = payload.replace("token=", "", 1).strip()
        ok, msg, grant_seconds, limit, payload_key = validate_limit_token(code)
        if not ok:
            await update.message.reply_text(f"❌ {msg}")
            return

        count = await get_token_usage(payload_key)
        if count >= limit:
            await update.message.reply_text("❌ Token already used max times.")
            return

        await set_verified_for_seconds(user_id, grant_seconds)
        await increment_token_usage(payload_key)

        days = grant_seconds // (24*3600)
        hours = (grant_seconds % (24*3600)) // 3600
        await update.message.reply_text(
            f"🎉 Verified!\n\n✅ Access: {days}d {hours}h\n🔑 Token: {count+1}/{limit}"
        )
        return

    if payload.startswith("verified="):
        code = payload.replace("verified=", "", 1).strip()
        if validate_code_anyuser(code):
            await set_verified_24h(user_id)
            await update.message.reply_text("🎉 Verified for 24h!", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Invalid/expired code.")
        return

    # ---------------- VIDEO ID(s) HANDLING ----------------
    if payload.isdigit() or "-" in payload or "&" in payload:
        video_ids = []

        if "-" in payload:
            try:
                start_id, end_id = map(int, payload.split("-"))
                if start_id <= end_id:
                    video_ids = list(range(start_id, end_id + 1))
            except Exception:
                await update.message.reply_text("❌ Invalid range format.")
                return

        elif "&" in payload:
            try:
                video_ids = [int(x) for x in payload.split("&") if x.isdigit()]
            except Exception:
                await update.message.reply_text("❌ Invalid multi-ID format.")
                return

        else:
            video_ids = [int(payload)]

        if not await check_user_in_channels(context.bot, user_id):
            keyboard = [[InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{ch.replace('@','')}")] for ch in JOIN_CHANNELS]
            keyboard.append([InlineKeyboardButton("🔄 I Joined, Retry", callback_data="check_join")])
            await update.message.reply_text("🔒 Join required channels.", reply_markup=InlineKeyboardMarkup(keyboard))
            return

        if await is_verified(user_id):
            sent = 0
            for vid in video_ids:
                try:
                    msg = await context.bot.copy_message(
                        chat_id=user_id,
                        from_chat_id=SOURCE_CHANNEL,
                        message_id=vid,
                        protect_content=True
                    )
                    sent += 1

                    # ✅ Track for auto-delete
                    await add_sent_message(user_id, msg.message_id, time.time() + 12 * 3600)

                except Exception as e:
                    await update.message.reply_text(f"⚠️ Couldn’t send video ID {vid}. Error: {e}")
            if sent > 0:
                await update.message.reply_text(f"✅ Sent {sent} video(s).")
        else:
            await update.message.reply_text(
                "🔒 Verify first to unlock video access.",
                reply_markup=verify_menu_kb()
            )
        return

# ---------------- CALLBACK HANDLERS ----------------
async def join_check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    username = query.from_user.first_name or "User"
    await query.answer()

    if not await check_user_in_channels(context.bot, user_id):
        keyboard = [[InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{ch.replace('@','')}")] for ch in JOIN_CHANNELS]
        keyboard.append([InlineKeyboardButton("🔄 Retry", callback_data="check_join")])
        await query.edit_message_text(
            f"👋 Hi {username}, please join all required channels.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        if await is_verified(user_id):
            await query.edit_message_text("✅ You’re already verified!", parse_mode="Markdown")
        else:
            await query.edit_message_text(
                f"👋 Welcome {username}! Please verify for 24h access.",
                reply_markup=verify_menu_kb(),
                parse_mode="Markdown"
            )

async def remove_ads_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    text = (
        "✨ Premium Membership Plans:\n\n"
        "• 7 Days – ₹30\n"
        "• 1 Month – ₹110\n"
        "• 3 Months – ₹299\n"
        "• 6 Months – ₹550\n"
        "• 1 Year – ₹999\n\n"
        "💵 Pay via UPI: `roshanbot@fam`\n"
    )
    keyboard = [
        [InlineKeyboardButton("📤 Send Screenshot(Admin)", url="https://t.me/Instahubpaymentcheckbot")],
        [InlineKeyboardButton("❌ Close", callback_data="close_ads")]
    ]
    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def close_ads_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()
    if await is_verified(user_id):
        await query.edit_message_text("✅ You’re verified!", parse_mode="Markdown")
    else:
        await query.edit_message_text("👋 Please verify to unlock 24h access.", reply_markup=verify_menu_kb())

# ---------------- VERIFIED ----------------
async def verified_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id

    code = None
    if text.startswith("/verified="):
        code = text.replace("/verified=", "", 1).strip()
    elif text.startswith("/verified "):
        code = text.split(" ", 1)[1].strip()

    if not code:
        await update.message.reply_text("⚠️ Use: `/verified=YOUR_CODE`")
        return

    if validate_code_anyuser(code):
        await set_verified_24h(user_id)
        await update.message.reply_text("🎉 Verified for 24h!", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Invalid or expired code.")

# ---------------- REDEEM ----------------
async def redeem_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id
    parts = text.split(maxsplit=1)

    if len(parts) < 2:
        await update.message.reply_text("⚠️ Usage:\n`/redeem <TOKEN>`")
        return
    token = parts[1].strip()

    ok, msg, grant_seconds = validate_premium_token_for_user(token, user_id)
    if ok:
        await set_verified_for_seconds(user_id, grant_seconds)
        days = grant_seconds // (24*3600)
        hours = (grant_seconds % (24*3600)) // 3600
        await update.message.reply_text(f"🎉 Premium redeemed! ✅ Access {days}d {hours}h")
    else:
        await update.message.reply_text(f"❌ {msg}")

# ---------------- MAIN ----------------
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("verified", verified_handler))
    app.add_handler(CommandHandler("redeem", redeem_handler))
    app.add_handler(CallbackQueryHandler(join_check_callback, pattern="check_join"))
    app.add_handler(CallbackQueryHandler(remove_ads_callback, pattern="remove_ads"))
    app.add_handler(CallbackQueryHandler(close_ads_callback, pattern="close_ads"))

    loop = asyncio.get_event_loop()
    loop.run_until_complete(init_db())
    loop.create_task(auto_delete_task(app))

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
