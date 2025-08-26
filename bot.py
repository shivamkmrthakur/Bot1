#!/usr/bin/env python3
# bot_verify.py

import os
import json
import time
import hmac
import hashlib
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes

# ----------------- CONFIG -----------------
TOKEN = "8409312798:AAF9aVNMdSynS5ndEOiyKe8Bc2NDe3dNk1I"
SOURCE_CHANNEL = "@botdatabase1"
VERIFY_FILE = "verified_users.json"

# Secret key (must match client-side)
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

async def send_verify_buttons(update: Update, note: str = None):
    keyboard = [
        [InlineKeyboardButton("✅ Verify (open site)", url="https://your-site.com/verify.html")],
        [InlineKeyboardButton("ℹ️ How to Verify", url="https://your-site.com/howto.html")]
    ]
    text = "⚠️ Please verify first using the verification link on our website."
    if note:
        text = note + "\n\n" + text
    await update.message.reply_text(text, reply_markup=InlineKeyboardMarkup(keyboard))

async def start_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    user_id = update.effective_user.id

    if text == "/start":
        keyboard = [[InlineKeyboardButton("✅ Verify (open site)", url="https://your-site.com/verify.html")]]
        await update.message.reply_text(
            "👉 Usage:\n"
            "`/start <video_id>` — request a lecture (bot will forward if you are verified)\n\n"
            "Or verify first by visiting our website and then returning to the bot.",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if " " in text:
        payload = text.split(" ", 1)[1].strip()
    else:
        payload = text[len("/start"):].strip()

    if payload.startswith("verified="):
        code = payload.replace("verified=", "", 1).strip()
        if validate_code_anyuser(code):
            set_verified(user_id)
            video_id = context.user_data.get("video_id")
            if video_id:
                try:
                    await context.bot.forward_message(chat_id=user_id, from_chat_id=SOURCE_CHANNEL, message_id=int(video_id))
                    await update.message.reply_text("✅ Verified — and here is your lecture.")
                except Exception as e:
                    await update.message.reply_text(f"✅ Verified for 24h, but error sending lecture: {e}")
            else:
                await update.message.reply_text("✅ Verified for 24 hours! Now send `/start <video_id>` to get your lecture.", parse_mode="Markdown")
        else:
            await update.message.reply_text("❌ Invalid or expired verification code. Please get a new code from the website.")
        return

    if payload.isdigit():
        video_id = payload
        context.user_data["video_id"] = video_id
        if is_verified(user_id):
            try:
                await context.bot.forward_message(chat_id=user_id, from_chat_id=SOURCE_CHANNEL, message_id=int(video_id))
                await update.message.reply_text("✅ Here is your lecture.")
            except Exception as e:
                await update.message.reply_text(f"❌ Error forwarding video. Details: {e}")
        else:
            await send_verify_buttons(update, note="🔒 You are not verified yet.")
    else:
        await update.message.reply_text("❌ Invalid command. Use `/start <video_id>` or verify via website.", parse_mode="Markdown")

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
        video_id = context.user_data.get("video_id")
        if video_id:
            try:
                await context.bot.forward_message(chat_id=user_id, from_chat_id=SOURCE_CHANNEL, message_id=int(video_id))
                await update.message.reply_text("✅ Verified — and here is your lecture.")
            except Exception as e:
                await update.message.reply_text(f"✅ Verified for 24h, but error sending lecture: {e}")
        else:
            await update.message.reply_text("✅ Verified for 24 hours! Now send `/start <video_id>` to get your lecture.")
    else:
        await update.message.reply_text("❌ Invalid or expired verification code. Please generate a fresh code from the website.")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start_handler))
    app.add_handler(CommandHandler("verified", verified_handler))
    print("Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
