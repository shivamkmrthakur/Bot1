#!/usr/bin/env python3
# bot.py

import os
import json
import time
import hmac
import hashlib
import base64
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# ----------------- CONFIG -----------------
TOKEN = "8409312798:AAErfYLxziXCDEtZWGHj8JFStG1_Vn2uNWg"
SOURCE_CHANNEL = -1002934836217
JOIN_CHANNELS = ["@instahubackup", "@instahubackup2"]

VERIFY_FILE = "verified_users.json"
SECRET_KEY = b"G7r9Xm2qT5vB8zN4pL0sQwE6yH1uR3cKfVb9ZaP2"
REDEEM_WINDOW_SECONDS = 3 * 60 * 60

TOKEN_USAGE_FILE = "token_usage.json"
SENT_VIDEOS_FILE = "sent_videos.json"
ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
DELETE_AFTER_SECONDS = 12 * 3600  # 12 hours

# ---------------- HELPER FILE LOAD/SAVE -----------------
def load_json(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_json(file_path, data):
    with open(file_path, "w") as f:
        json.dump(data, f)

def load_verified():
    return load_json(VERIFY_FILE)

def save_verified(data):
    save_json(VERIFY_FILE, data)

def load_token_usage():
    return load_json(TOKEN_USAGE_FILE)

def save_token_usage(data):
    save_json(TOKEN_USAGE_FILE, data)

def load_sent_videos():
    return load_json(SENT_VIDEOS_FILE)

def save_sent_videos(data):
    save_json(SENT_VIDEOS_FILE, data)

# ----------------- VERIFICATION -----------------
def set_verified_for_seconds(user_id: int, seconds: int):
    verified = load_verified()
    now = time.time()
    current_expiry = verified.get(str(user_id), 0)
    verified[str(user_id)] = max(now, current_expiry) + seconds
    save_verified(verified)

def set_verified_24h(user_id: int):
    set_verified_for_seconds(user_id, 24*3600)

def is_verified(user_id: int):
    verified = load_verified()
    key = str(user_id)
    if key in verified:
        if time.time() < verified[key]:
            return True
        del verified[key]
        save_verified(verified)
    return False

# ----------------- TOKEN VALIDATION -----------------
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

    if ddmmyy != time.strftime("%d%m%y"):
        return False, "❌ Token expired or invalid date.", 0, 0, ""

    grant_seconds = days*24*3600 + hours*3600
    if grant_seconds <= 0:
        return False, "❌ Duration must be positive.", 0, 0, ""

    return True, "OK", grant_seconds, limit, raw

def build_premium_token_payload(user_id: int, days: int, hours: int, ts: int) -> str:
    return f"{ts}|{user_id}|{days}|{hours}"

def sign_payload_hex(payload: str) -> str:
    return hmac.new(SECRET_KEY, payload.encode(), hashlib.sha256).hexdigest()

def decode_premium_token(token_b64: str):
    try:
        raw = base64.b64decode(token_b64).decode()
    except:
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

    grant_seconds = days*24*3600 + hours*3600
    if grant_seconds <= 0:
        return False, "Duration must be positive.", 0

    return True, "OK", grant_seconds

# ----------------- CHANNEL CHECK -----------------
async def check_user_in_channels(bot, user_id):
    for channel in JOIN_CHANNELS:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status in ["left", "kicked"]:
                return False
        except:
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

# ----------------- AUTO DELETE TASK -----------------
async def auto_delete_task(bot):
    while True:
        sent_videos = load_sent_videos()
        now = time.time()
        to_delete = []

        for msg_id, info in sent_videos.items():
            if now - info["sent_at"] >= DELETE_AFTER_SECONDS:
                try:
                    await bot.delete_message(chat_id=info["chat_id"], message_id=int(msg_id))
                except:
                    pass
                to_delete.append(msg_id)

        for msg_id in to_delete:
            sent_videos.pop(msg_id, None)

        save_sent_videos(sent_videos)
        await asyncio.sleep(60)

# ----------------- HANDLERS -----------------
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id
    username = update.effective_user.first_name or "User"

    if text.startswith("/start"):
        # JOIN CHECK
        if not await check_user_in_channels(context.bot, user_id):
            keyboard = [[InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{ch.replace('@','')}")] for ch in JOIN_CHANNELS]
            keyboard.append([InlineKeyboardButton("🔄 I Joined, Retry", callback_data="check_join")])
            await update.message.reply_text(
                f"👋 Hi {username}!\n\nJoin all required channels first.\nThen hit Retry.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        if is_verified(user_id):
            await update.message.reply_text(
                "✅ You’re already verified!\n\nGo to [@Instaa_hubb](https://t.me/instaa_hubb) and pick a video.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text(
                f"👋 Welcome {username}!\n\nPlease verify to unlock 24-hour access.",
                reply_markup=verify_menu_kb(),
                parse_mode="Markdown"
            )
        return

    # HANDLE PAYLOADS
    payload = text.split(" ", 1)[1].strip() if " " in text else text[len("/start"):].strip()

    # HATCHED TOKEN
    if payload.startswith("token="):
        code = payload.replace("token=", "", 1).strip()
        ok, msg, grant_seconds, limit, payload_key = validate_limit_token(code)
        if not ok:
            await update.message.reply_text(f"❌ {msg}")
            return

        usage = load_token_usage()
        count = usage.get(payload_key, 0)
        if count >= limit:
            await update.message.reply_text("❌ Token already used maximum times.")
            return

        set_verified_for_seconds(user_id, grant_seconds)
        usage[payload_key] = count + 1
        save_token_usage(usage)

        days = grant_seconds // (24*3600)
        hours = (grant_seconds % (24*3600)) // 3600
        await update.message.reply_text(
            f"🎉 Verified! Access: {days}d {hours}h\n"
            f"Token usage: {usage[payload_key]}/{limit}"
        )
        return

    # VERIFIED=CODE
    if payload.startswith("verified="):
        code = payload.replace("verified=", "", 1).strip()
        if validate_code_anyuser(code):
            set_verified_24h(user_id)
            await update.message.reply_text(
                "🎉 Verification successful for 24h!",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ Invalid or expired code.")
        return

    # VIDEO ID(s)
    if payload.isdigit() or "-" in payload or "&" in payload:
        video_ids = []
        if "-" in payload:
            try:
                start_id, end_id = map(int, payload.split("-"))
                video_ids = list(range(start_id, end_id+1))
            except:
                await update.message.reply_text("❌ Invalid range.")
                return
        elif "&" in payload:
            try:
                video_ids = [int(x) for x in payload.split("&") if x.isdigit()]
            except:
                await update.message.reply_text("❌ Invalid multi-ID format.")
                return
        else:
            video_ids = [int(payload)]

        # JOIN CHECK
        if not await check_user_in_channels(context.bot, user_id):
            keyboard = [[InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{ch.replace('@','')}")] for ch in JOIN_CHANNELS]
            keyboard.append([InlineKeyboardButton("🔄 I Joined, Retry", callback_data="check_join")])
            await update.message.reply_text("🔒 Join all channels first.", reply_markup=InlineKeyboardMarkup(keyboard))
            return

        if is_verified(user_id):
            sent = 0
            sent_videos = load_sent_videos()
            for vid in video_ids:
                try:
                    msg = await context.bot.copy_message(
                        chat_id=user_id,
                        from_chat_id=SOURCE_CHANNEL,
                        message_id=vid,
                        protect_content=True
                    )
                    # TRACK FOR AUTO-DELETE
                    sent_videos[str(msg.message_id)] = {"chat_id": user_id, "sent_at": time.time()}
                    sent += 1
                except Exception as e:
                    await update.message.reply_text(f"⚠️ Couldn't send video {vid}. Error: {e}")
            save_sent_videos(sent_videos)
            if sent > 0:
                await update.message.reply_text(f"✅ Sent {sent} video(s). Will auto-delete in 12 hours.")
        else:
            await update.message.reply_text(
                "🔒 You haven't verified yet.",
                reply_markup=verify_menu_kb()
            )
        return

# ----------------- CALLBACKS -----------------
async def join_check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    username = query.from_user.first_name or "User"

    if not await check_user_in_channels(context.bot, user_id):
        keyboard = [[InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{ch.replace('@','')}")] for ch in JOIN_CHANNELS]
        keyboard.append([InlineKeyboardButton("🔄 Retry", callback_data="check_join")])
        await query.edit_message_text(f"Hi {username}, join all channels first.", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        if is_verified(user_id):
            await query.edit_message_text("✅ Already verified! Pick videos at [@Instaa_hubb](https://t.me/instaa_hubb).", parse_mode="Markdown")
        else:
            await query.edit_message_text("👋 Please verify for 24h access.", reply_markup=verify_menu_kb(), parse_mode="Markdown")

# ----------------- VERIFIED HANDLER -----------------
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
        set_verified_24h(user_id)
        await update.message.reply_text("🎉 Verified for 24h!", parse_mode="Markdown")
    else:
        await update.message.reply_text("❌ Invalid or expired code.")

# ----------------- REDEEM HANDLER -----------------
async def redeem_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id
    parts = text.split(maxsplit=1)

    if len(parts) < 2:
        await update.message.reply_text("⚠️ Usage: `/redeem <TOKEN>`")
        return
    token = parts[1].strip()
    ok, msg, grant_seconds = validate_premium_token_for_user(token, user_id)
    if ok:
        set_verified_for_seconds(user_id, grant_seconds)
        days = grant_seconds // (24*3600)
        hours = (grant_seconds % (24*3600)) // 3600
        await update.message.reply_text(f"🎉 Premium redeemed!\n✅ Verified for {days}d {hours}h")
    else:
        await update.message.reply_text(f"❌ {msg}")

# ----------------- MAIN -----------------
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("verified", verified_handler))
    app.add_handler(CommandHandler("redeem", redeem_handler))
    app.add_handler(CallbackQueryHandler(join_check_callback, pattern="check_join"))

    # Start auto-delete background task
    app.job_queue.run_repeating(lambda ctx: asyncio.create_task(auto_delete_task(app.bot)), interval=60, first=0)

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
