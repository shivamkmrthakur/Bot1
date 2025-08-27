#!/usr/bin/env python3
# bot.py

import os
import json
import time
import hmac
import hashlib
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# ----------------- CONFIG -----------------
TOKEN = "8409312798:AAF9aVNMdSynS5ndEOiyKe8Bc2NDe3dNk1I"
SOURCE_CHANNEL = "@botdatabase1"   # jaha se video forward hoga
JOIN_CHANNELS = ["@instahubackup", "@instahubackup2"]  # required channels

VERIFY_FILE = "verified_users.json"
SECRET_KEY = b"G7r9Xm2qT5vB8zN4pL0sQwE6yH1uR3cKfVb9ZaP2"
SIG_LEN = 12
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

def set_verified(user_id):
    verified = load_verified()
    verified[str(user_id)] = time.time() + 24 * 60 * 60
    save_verified(verified)

def is_verified(user_id):
    verified = load_verified()
    key = str(user_id)
    if key in verified:
        if time.time() < verified[key]:
            return True
        del verified[key]
        save_verified(verified)
    return False

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

# ---------------- HELPERS ----------------
async def check_user_in_channels(bot, user_id):
    """Check if user is in all required JOIN_CHANNELS"""
    for channel in JOIN_CHANNELS:
        try:
            member = await bot.get_chat_member(channel, user_id)
            if member.status in ["left", "kicked"]:
                return False
        except Exception:
            return False
    return True

# ---------------- HANDLERS ----------------
async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id
    username = update.effective_user.first_name or "User"

    # ---- If only "/start" (no video id) ----
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
            await update.message.reply_text(
                "👉 Go to my channel and click on the video you want. After that I will send you the video."
            )
        else:
            keyboard = [
                [
                    InlineKeyboardButton("✅ Verify (open site)", url="https://adrinolinks.com/NmL2Y"),
                    InlineKeyboardButton("ℹ️ How to Verify?", url="https://your-site.com/how-to-verify.html")
                ],
                [InlineKeyboardButton("🚫 Remove Ads (One Click)", callback_data="remove_ads")]
            ]
            await update.message.reply_text(
                f"👋 Hello {username}!\n\n"
                "Welcome to the InstaHub bot.\n\n"
                "Please verify yourself first to access video for 24 h",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return

    # ---- If "/start <something>" ----
    if " " in text:
        payload = text.split(" ", 1)[1].strip()
    else:
        payload = text[len("/start"):].strip()

    # verification payload
    if payload.startswith("verified="):
        code = payload.replace("verified=", "", 1).strip()
        if validate_code_anyuser(code):
            set_verified(user_id)
            await update.message.reply_text(
                "✅ Verified for 24 hours! Now Go to my channel and watch the video you want.",
                parse_mode="Markdown"
            )
        else:
            await update.message.reply_text("❌ Invalid or expired verification code.")
        return

    # if user sends /start <video_id>
    if payload.isdigit():
        video_id = payload
        context.user_data["video_id"] = video_id

        if not await check_user_in_channels(context.bot, user_id):
            keyboard = [[InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{ch.replace('@','')}")] for ch in JOIN_CHANNELS]
            keyboard.append([InlineKeyboardButton("🔄 Try Again", callback_data="check_join")])
            await update.message.reply_text(
                "🔒 You must join all required channels first.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
            return

        if is_verified(user_id):
            try:
                await context.bot.forward_message(chat_id=user_id, from_chat_id=SOURCE_CHANNEL, message_id=int(video_id))
                await update.message.reply_text("✅ Here is your video")
            except Exception as e:
                await update.message.reply_text(f"❌ Error forwarding video. Details: {e}")
        else:
            keyboard = [
                [
                    InlineKeyboardButton("✅ Verify (open site)", url="https://adrinolinks.com/NmL2Y"),
                    InlineKeyboardButton("ℹ️ How to Verify?", url="https://your-site.com/how-to-verify.html")
                ],
                [InlineKeyboardButton("🚫 Remove Ads (One Click)", callback_data="remove_ads")]
            ]
            await update.message.reply_text(
                "🔒 You are not verified yet.\n\n"
                "Please verify yourself first to get videos.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    else:
        await update.message.reply_text("❌ Invalid command. Go to my channel and then watch your videos.", parse_mode="Markdown")

# ---------------- CALLBACK HANDLERS ----------------
async def join_check_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    username = query.from_user.first_name or "User"

    await query.answer()  # remove loading state

    if not await check_user_in_channels(context.bot, user_id):
        keyboard = [[InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{ch.replace('@','')}")] for ch in JOIN_CHANNELS]
        keyboard.append([InlineKeyboardButton("🔄 Try Again", callback_data="check_join")])
        await query.edit_message_text(
            f"👋 Hello {username}\n\n"
            "You still need to join my Channel/Group.\n\n"
            "Kindly please join below 👇",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        if is_verified(user_id):
            await query.edit_message_text(
                "👉 Go to my channel and click on the video you want. After that I will send you the video."
            )
        else:
            keyboard = [
                [
                    InlineKeyboardButton("✅ Verify (open site)", url="https://adrinolinks.com/NmL2Y"),
                    InlineKeyboardButton("ℹ️ How to Verify?", url="https://your-site.com/how-to-verify.html")
                ],
                [InlineKeyboardButton("🚫 Remove Ads (One Click)", callback_data="remove_ads")]
            ]
            await query.edit_message_text(
                f"👋 Hello {username}!\n\n"
                "Welcome to the InstaHub bot.\n\n"
                "Please verify yourself first to access video for 24 h",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )

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
        "💵 UPI ID 1 -  Lays@slc\n\n"
        "💵 UPI ID 2 - wtf69kartik@fam (Tap to copy)\n\n"
        "📸 [Click here to scan QR](https://files.catbox.moe/4dee5y.jpg)\n\n"
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
        await query.edit_message_text(
            "👉 Go to my channel and click on the video you want. After that I will send you the video."
        )
    else:
        keyboard = [
            [
                InlineKeyboardButton("✅ Verify (open site)", url="https://adrinolinks.com/NmL2Y"),
                InlineKeyboardButton("ℹ️ How to Verify?", url="https://your-site.com/how-to-verify.html")
            ],
            [InlineKeyboardButton("🚫 Remove Ads (One Click)", callback_data="remove_ads")]
        ]
        await query.edit_message_text(
            f"👋 Hello {username}!\n\n"
            "Welcome to the InstaHub bot.\n\n"
            "Please verify yourself first to access video for 24 h",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ---------------- VERIFIED HANDLER ----------------
async def verified_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
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
        set_verified(user_id)
        await update.message.reply_text(
            "✅ Verified for 24 hours! Now you can receive your requested videos."
        )
    else:
        await update.message.reply_text("❌ Invalid or expired verification code.")

# ---------------- MAIN ----------------
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("verified", verified_handler))
    app.add_handler(CallbackQueryHandler(join_check_callback, pattern="check_join"))
    app.add_handler(CallbackQueryHandler(remove_ads_callback, pattern="remove_ads"))
    app.add_handler(CallbackQueryHandler(close_ads_callback, pattern="close_ads"))

    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
