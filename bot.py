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
SOURCE_CHANNEL = "@botdatabase1"
JOIN_CHANNELS = ["@instahubackup", "@instahubackup2"]

VERIFY_FILE = "verified_users.json"

# SECRET_KEY must match the HTML generator's key
SECRET_KEY = b"G7r9Xm2qT5vB8zN4pL0sQwE6yH1uR3cKfVb9ZaP2"
# how many seconds a generated code may be redeemed after creation (3 hours)
REDEEM_WINDOW_SECONDS = 3 * 60 * 60
# signature representation: hex string (full sha256 hex). We store/compare full hex.
# You can truncate if you want, but full hex is fine.
# ------------------------------------------

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
    # extend from existing expiry if already verified in future
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
        # expired -> cleanup
        del verified[key]
        save_verified(verified)
    return False

# ---------------- legacy validate (free short-code) ----------------
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

# ---------------- premium opaque-code helpers ----------------
def build_premium_token_payload(user_id: int, days: int, hours: int, ts: int) -> str:
    # payload format: "<ts>|<user_id>|<days>|<hours>"
    return f"{ts}|{user_id}|{days}|{hours}"

def sign_payload_hex(payload: str) -> str:
    return hmac.new(SECRET_KEY, payload.encode(), hashlib.sha256).hexdigest()

def encode_premium_token(payload: str, hex_sig: str) -> str:
    combined = f"{payload}|{hex_sig}"
    return base64.b64encode(combined.encode()).decode()

def decode_premium_token(token_b64: str):
    """
    returns (ok, msg, payload_str, hex_sig)
    """
    try:
        raw = base64.b64decode(token_b64).decode()
    except Exception:
        return False, "Token is not valid base64.", None, None
    if "|" not in raw:
        return False, "Token payload malformed.", None, None
    # signature is last '|' separated part
    parts = raw.rsplit("|", 1)
    if len(parts) != 2:
        return False, "Token malformed.", None, None
    payload, hex_sig = parts
    if not hex_sig or len(hex_sig) < 10:
        return False, "Invalid signature part.", None, None
    return True, "OK", payload, hex_sig

def validate_premium_token_for_user(token_b64: str, actual_user_id: int):
    """
    returns (ok:bool, msg:str, grant_seconds:int)
    """
    ok, msg, payload, hex_sig = decode_premium_token(token_b64)
    if not ok:
        return False, msg, 0

    # payload format: ts|user_id|days|hours
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

    # user match
    if uid != actual_user_id:
        return False, "Token is not for this user.", 0

    # redeem window
    if time.time() - ts > REDEEM_WINDOW_SECONDS:
        return False, "Token redeem window (3h) has passed.", 0

    # verify signature
    expected_hex = sign_payload_hex(payload)
    if not hmac.compare_digest(expected_hex, hex_sig):
        return False, "Signature mismatch.", 0

    # compute grant
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
            InlineKeyboardButton("✅ Verify (open site)", url="https://adrinolinks.com/NmL2Y"),
            InlineKeyboardButton("ℹ️ How to Verify?", url="https://your-site.com/how-to-verify.html")
        ],
        [InlineKeyboardButton("🚫 Remove Ads (One Click)", callback_data="remove_ads")]
    ])

# ---------------- HANDLERS ----------------
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id
    username = update.effective_user.first_name or "User"

    # /start base
    if text == "/start":
        if not await check_user_in_channels(context.bot, user_id):
            keyboard = [[InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{ch.replace('@','')}")] for ch in JOIN_CHANNELS]
            keyboard.append([InlineKeyboardButton("🔄 Try Again", callback_data="check_join")])
            await update.message.reply_text(
                f"👋 Hello {username}\n\n"
                "You need to join my Channel/Group to use me.\n\n"
                "Kindly please join below 👇",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        if is_verified(user_id):
            await update.message.reply_text("👉 Go to my channel and click on the video you want. After that I will send you the video.")
        else:
            await update.message.reply_text(
                f"👋 Hello {username}!\n\nWelcome to the InstaHub bot.\n\nPlease verify yourself first to access video for 24 h",
                reply_markup=verify_menu_kb()
            )
        return

    # /start <payload> handling (legacy verified= or video id)
    if " " in text:
        payload = text.split(" ", 1)[1].strip()
    else:
        payload = text[len("/start"):].strip()

    # legacy short verified path (free flow)
    if payload.startswith("verified="):
        code = payload.replace("verified=", "", 1).strip()
        if validate_code_anyuser(code):
            set_verified_24h(user_id)
            await update.message.reply_text("✅ Verified for 24 hours! Now Go to my channel and watch the video you want.")
        else:
            await update.message.reply_text("❌ Invalid or expired verification code.")
        return

    # /start <video_id>
    if payload.isdigit():
        video_id = payload
        context.user_data["video_id"] = video_id

        if not await check_user_in_channels(context.bot, user_id):
            keyboard = [[InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{ch.replace('@','')}")] for ch in JOIN_CHANNELS]
            keyboard.append([InlineKeyboardButton("🔄 Try Again", callback_data="check_join")])
            await update.message.reply_text("🔒 You must join all required channels first.", reply_markup=InlineKeyboardMarkup(keyboard))
            return

        if is_verified(user_id):
            try:
                await context.bot.forward_message(chat_id=user_id, from_chat_id=SOURCE_CHANNEL, message_id=int(video_id))
                await update.message.reply_text("✅ Here is your video")
            except Exception as e:
                await update.message.reply_text(f"❌ Error forwarding video. Details: {e}")
        else:
            await update.message.reply_text("🔒 You are not verified yet.\n\nPlease verify yourself first to get videos.", reply_markup=verify_menu_kb())
    else:
        await update.message.reply_text("❌ Invalid command. Go to my channel and then watch your videos.", parse_mode="Markdown")

# ---------------- CALLBACK HANDLERS ----------------
async def join_check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    username = query.from_user.first_name or "User"
    await query.answer()

    if not await check_user_in_channels(context.bot, user_id):
        keyboard = [[InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{ch.replace('@','')}")] for ch in JOIN_CHANNELS]
        keyboard.append([InlineKeyboardButton("🔄 Try Again", callback_data="check_join")])
        await query.edit_message_text(f"👋 Hello {username}\n\nYou still need to join my Channel/Group.\n\nKindly please join below 👇", reply_markup=InlineKeyboardMarkup(keyboard))
    else:
        if is_verified(user_id):
            await query.edit_message_text("👉 Go to my channel and click on the video you want. After that I will send you the video.")
        else:
            await query.edit_message_text(f"👋 Hello {username}!\n\nWelcome to the InstaHub bot.\n\nPlease verify yourself first to access video for 24 h", reply_markup=verify_menu_kb())

async def remove_ads_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    username = query.from_user.first_name or "User"
    await query.answer()

    text = (
        f"👋 Hey {username}\n\n"
        "🎖️ Available Plans :\n\n"
        "● 30 rs For 7 Days Prime Membership\n\n"
        "● 110 rs For 1 Month Prime Membership\n\n"
        "● 299 rs For 3 Months Prime Membership\n\n"
        "● 550 rs For 6 Months Prime Membership\n\n"
        "● 999 rs For 1 Year Prime Membership\n\n"
        "💵 UPI ID - roshanbot@fam (Tap to copy)\n\n"
        "📸 [Click here to scan QR](https://insta-hub.netlify.app/qr.png)\n\n"
        "♻️ If payment is not getting sent on above given QR code then inform admin.\n\n"
        "‼️ Must send screenshot after payment."
    )

    keyboard = [
        [InlineKeyboardButton("📤 Send Screenshot", url="https://t.me/your_admin_username")],
        [InlineKeyboardButton("❌ Close", callback_data="close_ads")]
    ]

    await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))

async def close_ads_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    username = query.from_user.first_name or "User"
    await query.answer()

    if is_verified(user_id):
        await query.edit_message_text("👉 Go to my channel and click on the video you want. After that I will send you the video.")
    else:
        await query.edit_message_text(f"👋 Hello {username}!\n\nWelcome to the InstaHub bot.\n\nPlease verify yourself first to access video for 24 h", reply_markup=verify_menu_kb())

# ---------------- VERIFIED (legacy) ----------------
async def verified_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id

    code = None
    if text.startswith("/verified="):
        code = text.replace("/verified=", "", 1).strip()
    elif text.startswith("/verified "):
        code = text.split(" ", 1)[1].strip()

    if not code:
        await update.message.reply_text("❌ Invalid format. Use `/verified=CODE`.")
        return

    if validate_code_anyuser(code):
        set_verified_24h(user_id)
        await update.message.reply_text("✅ Verified for 24 hours! Now you can receive your requested videos.")
    else:
        await update.message.reply_text("❌ Invalid or expired verification code.")

# ---------------- REDEEM (premium opaque tokens) ----------------
async def redeem_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = (update.message.text or "").strip()
    user_id = update.effective_user.id
    parts = text.split(maxsplit=1)

    if len(parts) < 2:
        await update.message.reply_text("❌ Usage: /redeem <TOKEN>")
        return
    token = parts[1].strip()

    ok, msg, grant_seconds = validate_premium_token_for_user(token, user_id)
    if ok:
        set_verified_for_seconds(user_id, grant_seconds)
        # convert seconds into days+hours for message
        days = grant_seconds // (24*3600)
        hours = (grant_seconds % (24*3600)) // 3600
        await update.message.reply_text(f"✅ Premium redeemed! You are verified for {days} day(s) and {hours} hour(s). Enjoy.")
    else:
        await update.message.reply_text(f"❌ {msg}")

# ---------------- MAIN ----------------
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("verified", verified_handler))
    app.add_handler(CommandHandler("redeem", redeem_handler))   # premium redeem
    app.add_handler(CallbackQueryHandler(join_check_callback, pattern="check_join"))
    app.add_handler(CallbackQueryHandler(remove_ads_callback, pattern="remove_ads"))
    app.add_handler(CallbackQueryHandler(close_ads_callback, pattern="close_ads"))

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
