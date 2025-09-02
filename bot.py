#!/usr/bin/env python3
# bot.py — Full version with all features + fixes + logging

import os
import json
import time
import hmac
import hashlib
import base64
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler
import psycopg2
from datetime import datetime, timedelta

# ---------------- DB CONNECTION (Postgres) ----------------
# Use Railway env var if set, else fallback to provided URL
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:dxQLpasirfqfmuBNoWCUomgQmIIGjPmK@yamabiko.proxy.rlwy.net:55695/railway")
conn = psycopg2.connect(DB_URL, sslmode="require")
cur = conn.cursor()

# Ensure tables exist
cur.execute("""
CREATE TABLE IF NOT EXISTS verified_users (
    user_id BIGINT PRIMARY KEY,
    expiry TIMESTAMP NOT NULL
);
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS token_usage (
    token_key TEXT PRIMARY KEY,
    used_count INT NOT NULL DEFAULT 0
);
""")
cur.execute("""
CREATE TABLE IF NOT EXISTS sent_videos (
    user_id BIGINT,
    msg_id BIGINT,
    sent_time TIMESTAMP NOT NULL,
    PRIMARY KEY (user_id, msg_id)
);
""")
conn.commit()


# ----------------- CONFIG -----------------
TOKEN = "8409312798:AAErfYLxziXCDEtZWGHj8JFStG1_Vn2uNWg"
SOURCE_CHANNEL = -1002934836217
JOIN_CHANNELS = ["@instahubackup", "@instahubackup2"]

VERIFY_FILE = "verified_users.json"

SECRET_KEY = b"G7r9Xm2qT5vB8zN4pL0sQwE6yH1uR3cKfVb9ZaP2"
REDEEM_WINDOW_SECONDS = 3 * 60 * 60

# ---------------- NEW: hatched short-token system ----------------
TOKEN_USAGE_FILE = "token_usage.json"
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

# ---------------- AUTO DELETE VIDEO AFTER 12H ----------------
VIDEO_LOG_FILE = "sent_videos.json"
VIDEO_EXPIRY_SECONDS = 12 * 60 * 60   # 12 hours

# ---------------- UTIL: JSON safe I/O ----------------
def _safe_load_json(path: str, default):
    if os.path.exists(path):
        try:
            with open(path, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"[WARN] Could not read {path}: {e}")
            return default
    return default


def _safe_save_json(path: str, data):
    try:
        with open(path, "w") as f:
            json.dump(data, f)
    except Exception as e:
        print(f"[ERROR] Could not write {path}: {e}")


# ---------------- VIDEO LOG ----------------
def load_sent_videos():
    return _safe_load_json(VIDEO_LOG_FILE, {})


def save_sent_videos(data):
    _safe_save_json(VIDEO_LOG_FILE, data)


async def log_sent_video(user_id: int, message_id: int):
    cur.execute(
        "INSERT INTO sent_videos (user_id, msg_id, sent_time) VALUES (%s, %s, %s) ON CONFLICT DO NOTHING",
        (user_id, message_id, datetime.utcnow())
    )
    conn.commit()
    print(f"[LOG] Video {message_id} logged for user {user_id}")

def load_token_usage():
    """Return token usage as a dict {token_key: used_count} from DB."""
    cur.execute("SELECT token_key, used_count FROM token_usage")
    rows = cur.fetchall()
    return {k: v for (k, v) in rows} if rows else {}

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


# ---------------- PREMIUM TOKEN HELPERS ----------------

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


# ---------------- VERIFY STORAGE ----------------

def load_verified():
    return _safe_load_json(VERIFY_FILE, {})


def save_verified(data):
    _safe_save_json(VERIFY_FILE, data)


def set_verified_for_seconds(user_id: int, seconds: int):
    expiry = datetime.utcnow() + timedelta(seconds=seconds)
    cur.execute(
        """
        INSERT INTO verified_users (user_id, expiry)
        VALUES (%s, %s)
        ON CONFLICT (user_id)
        DO UPDATE SET expiry = EXCLUDED.expiry
        """, (user_id, expiry)
    )
    conn.commit()
    print(f"[VERIFY] User {user_id} verified until {expiry}")

# ✅ NEW: helper to set exactly 24 hours
def set_verified_24h(user_id: int):
    """Shortcut to verify user for 24 hours."""
    set_verified_for_seconds(user_id, 24 * 3600)


# ✅ NEW: check verification status
def is_verified(user_id: int) -> bool:
    """Check if user is verified (expiry still valid)."""
    cur.execute("SELECT expiry FROM verified_users WHERE user_id = %s", (user_id,))
    row = cur.fetchone()
    if not row:
        return False
    expiry = row[0]
    return datetime.utcnow() < expiry

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

    print(f"[START] User {user_id} sent: {text}")

    if text == "/start":
        if not await check_user_in_channels(context.bot, user_id):
            keyboard = [[InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{ch.replace('@','')}")] for ch in JOIN_CHANNELS]
            keyboard.append([InlineKeyboardButton("🔄 I Joined, Retry", callback_data="check_join")])
            await update.message.reply_text(
                f"👋 Hi {username}!\n\nTo continue using this bot, please join all the required channels first.\n\n👉 Once done, tap **Retry** below.",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
            return

        if is_verified(user_id):
            await update.message.reply_text(
                "✅ You’re already verified!\n\nGo to [@Instaa_hubb](https://t.me/instaa_hubb), choose a video, and I’ll send it here for you.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"👋 Welcome {username}!\n\nThis bot helps you get videos from [@Instaa_hubb](https://t.me/instaa_hubb).\n\n🔒 Please verify yourself to unlock 24-hour access.",
                reply_markup=verify_menu_kb(),
                parse_mode="Markdown"
            )
        return

    # Handle verification payload (after /start <payload>)
    if " " in text:
        payload = text.split(" ", 1)[1].strip()
    else:
        payload = text[len("/start"):].strip() if text.startswith("/start") else text

    # ✅ NEW: Handle hatched multi-user tokens (short, scrambled)
    if payload.startswith("token="):
        code = payload.replace("token=", "", 1).strip()
        ok, msg, grant_seconds, limit, payload_key = validate_limit_token(code)
        if not ok:
            await update.message.reply_text(f"❌ {msg}")
            return

        usage = load_token_usage()
        count = usage.get(payload_key, 0)

        if count >= limit:
            await update.message.reply_text("❌ Sorry, this token has already been used by maximum users.")
            return

        set_verified_for_seconds(user_id, grant_seconds)
        usage[payload_key] = count + 1
        save_token_usage(usage)

        days = grant_seconds // (24*3600)
        hours = (grant_seconds % (24*3600)) // 3600
        await update.message.reply_text(
            f"🎉 Success! You’re now verified.\n\n✅ Access Granted for: {days} day(s) {hours} hour(s)\n🔑 Token usage: {usage[payload_key]}/{limit}\n\n👉 Now go back to [@Instaa_hubb](https://t.me/instaa_hubb) and select your video.",
            parse_mode="Markdown"
        )
        print(f"[TOKEN] limit-token used by {user_id}: {usage[payload_key]}/{limit}")
        return

    if payload.startswith("verified="):
        code = payload.replace("verified=", "", 1).strip()
        if validate_code_anyuser(code):
            set_verified_24h(user_id)
            await update.message.reply_text(
                "🎉 Verification successful! You’re now verified for 24 hours.\n\nGo back to [@Instaa_hubb](https://t.me/instaa_hubb) and pick your video.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ That verification code is invalid or expired.")
        return

    # ---------------- VIDEO ID(s) HANDLING ----------------
    if payload.isdigit() or "-" in payload or "&" in payload:
        video_ids = []

        if "-" in payload:  # range format e.g. 1-4
            try:
                start_id, end_id = map(int, payload.split("-"))
                if start_id <= end_id:
                    video_ids = list(range(start_id, end_id + 1))
            except Exception:
                await update.message.reply_text("❌ Invalid range format. Use like 1-4.")
                return

        elif "&" in payload:  # multiple specific IDs e.g. 1&2&5
            try:
                video_ids = [int(x) for x in payload.split("&") if x.isdigit()]
            except Exception:
                await update.message.reply_text("❌ Invalid multi-ID format. Use like 1&2&5.")
                return

        else:  # single id
            video_ids = [int(payload)]

        # Check join requirement
        if not await check_user_in_channels(context.bot, user_id):
            keyboard = [[InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{ch.replace('@','')}")] for ch in JOIN_CHANNELS]
            keyboard.append([InlineKeyboardButton("🔄 I Joined, Retry", callback_data="check_join")])
            await update.message.reply_text("🔒 Please join all required channels to continue.", reply_markup=InlineKeyboardMarkup(keyboard))
            return

        # Check verification
        if is_verified(user_id):
            sent = 0
            for vid in video_ids:
                try:
                    msg = await context.bot.copy_message(
                        chat_id=user_id,
                        from_chat_id=SOURCE_CHANNEL,
                        message_id=vid,
                        protect_content=True   # 🔒 Block forward + screenshot
                    )
                    await log_sent_video(user_id, msg.message_id)
                    sent += 1
                except Exception as e:
                    await update.message.reply_text(f"⚠️ Couldn’t send video ID {vid}. Error: {e}")
                    print(f"[SEND ERROR] user={user_id} vid={vid} err={e}")
            if sent > 0:
                await update.message.reply_text(f"✅ Sent {sent} video(s). They will auto-delete after 12 hours.")
        else:
            await update.message.reply_text(
                "🔒 You haven’t verified yet.\n\nPlease complete verification first to unlock video access.",
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
        keyboard.append([InlineKeyboardButton("🔄 I Joined, Retry", callback_data="check_join")])
        await query.edit_message_text(
            f"👋 Hi {username},\n\nYou still haven’t joined all the required channels.\n\n👉 Please join them and then hit Retry.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        if is_verified(user_id):
            await query.edit_message_text(
                "✅ You’re already verified!\n\nGo back to [@Instaa_hubb](https://t.me/instaa_hubb), choose a video, and I’ll deliver it here.",
                parse_mode="Markdown"
            )
        else:
            await query.edit_message_text(
                f"👋 Welcome {username}!\n\nBefore accessing videos, please verify yourself for 24-hour access at [@Instaa_hubb](https://t.me/instaa_hubb).",
                reply_markup=verify_menu_kb(),
                parse_mode="Markdown"
            )


async def remove_ads_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    username = query.from_user.first_name or "User"
    await query.answer()

    text = (
        f"👋 Hey {username},\n\n"
        "✨ Upgrade to **Premium Membership** and enjoy ad-free, unlimited access:\n\n"
        "📌 Plans:\n"
        "• 7 Days – ₹30\n"
        "• 1 Month – ₹110\n"
        "• 3 Months – ₹299\n"
        "• 6 Months – ₹550\n"
        "• 1 Year – ₹999\n\n"
        "💵 Pay via UPI ID: `roshanbot@fam`\n\n"
        "📸 [Scan QR Code](https://insta-hub.netlify.app/qr.png)\n\n"
        "⚠️ If payment fails on QR, contact the admin.\n\n"
        "📤 Don’t forget to send a payment screenshot after completing the transaction!"
    )

    keyboard = [
        [InlineKeyboardButton("📤 Send Screenshot(Admin)", url="https://t.me/Instahubpaymentcheckbot")],
        [InlineKeyboardButton("❌ Close", callback_data="close_ads")]
    ]

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))


async def close_ads_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    username = query.from_user.first_name or "User"
    await query.answer()

    if is_verified(user_id):
        await query.edit_message_text(
            "✅ You’re verified!\n\nGo back to [@Instaa_hubb](https://t.me/instaa_hubb), select a video, and I’ll send it here.",
            parse_mode="Markdown"
        )
    else:
        await query.edit_message_text(
            f"👋 Hi {username}!\n\nPlease complete verification first to unlock 24-hour video access.",
            reply_markup=verify_menu_kb()
        )


# ---------------- /verified ----------------
async def verified_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id

    code = None
    if text.startswith("/verified="):
        code = text.replace("/verified=", "", 1).strip()
    elif text.startswith("/verified "):
        code = text.split(" ", 1)[1].strip()

    if not code:
        await update.message.reply_text("⚠️ Invalid format.\n\nUse: `/verified=YOUR_CODE`", parse_mode="Markdown")
        return

    if validate_code_anyuser(code):
        set_verified_24h(user_id)
        await update.message.reply_text(
            "🎉 Success! You’re verified for the next 24 hours.\n\nGo back to [@Instaa_hubb](https://t.me/instaa_hubb) and request your videos.",
            parse_mode="Markdown"
        )
    else:
        await update.message.reply_text("❌ Invalid or expired verification code.")


# ---------------- /redeem ----------------
async def redeem_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id
    parts = text.split(maxsplit=1)

    if len(parts) < 2:
        await update.message.reply_text("⚠️ Usage:\n`/redeem <TOKEN>`", parse_mode="Markdown")
        return
    token = parts[1].strip()

    ok, msg, grant_seconds = validate_premium_token_for_user(token, user_id)
    if ok:
        set_verified_for_seconds(user_id, grant_seconds)
        days = grant_seconds // (24*3600)
        hours = (grant_seconds % (24*3600)) // 3600
        await update.message.reply_text(f"🎉 Premium redeemed!\n\n✅ You’re verified for {days} day(s) and {hours} hour(s). Enjoy your access!")
    else:
        await update.message.reply_text(f"❌ {msg}")


# ---------------- MAIN ----------------
def main():
    app = Application.builder().token(TOKEN).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("verified", verified_handler))
    app.add_handler(CommandHandler("redeem", redeem_handler))

    # Callback handlers
    app.add_handler(CallbackQueryHandler(join_check_callback, pattern="check_join"))
    app.add_handler(CallbackQueryHandler(remove_ads_callback, pattern="remove_ads"))
    app.add_handler(CallbackQueryHandler(close_ads_callback, pattern="close_ads"))

    # ✅ Start background cleaner (every 10 minutes)
    app.job_queue.run_repeating(lambda ctx: asyncio.create_task(cleanup_expired_videos(app.bot)), interval=600, first=10)

    print("[BOOT] Bot started and polling...")
    app.run_polling()


if __name__ == "__main__":
    main()
