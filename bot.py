#!/usr/bin/env python3
# bot.py

import os
import json
import time
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes, CallbackQueryHandler

# ----------------- CONFIG -----------------
TOKEN = "8409312798:AAF9aVNMdSynS5ndEOiyKe8Bc2NDe3dNk1I"
OWNER_ID = 7994709010  
SOURCE_CHANNEL = -1002934836217
JOIN_CHANNELS = ["@instahubackup", "@instahubackup2"]

# ----------------- FILE STORAGE -----------------
USER_FILE = "verified.json"

def load_users():
    if os.path.exists(USER_FILE):
        with open(USER_FILE, "r") as f:
            return json.load(f)
    return {}

def save_users(users):
    with open(USER_FILE, "w") as f:
        json.dump(users, f)

# ----------------- COMMANDS -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    users = load_users()
    if str(user.id) not in users:
        users[str(user.id)] = {"plan": "none", "expiry": 0}
        save_users(users)

    keyboard = [
        [InlineKeyboardButton("✅ Verify Now", callback_data="verify")],
        [InlineKeyboardButton("💎 Premium Plans", callback_data="premium")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        f"👋 Welcome <b>{user.first_name}</b> to <b>InstaHub</b>!\n\n"
        "🚀 Unlock unlimited access to our Insta tools.\n\n"
        "✅ First, verify by joining our channels.\n"
        "💎 Or get Premium for full access.\n\n"
        "👉 Click below to continue."
    )

    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode="HTML")

# ----------------- VERIFY -----------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "verify":
        # Check join requirement
        for ch in JOIN_CHANNELS:
            member = await context.bot.get_chat_member(chat_id=ch, user_id=query.from_user.id)
            if member.status not in ["member", "administrator", "creator"]:
                await query.message.reply_text(
                    f"❌ Please join {ch} first and then try again."
                )
                return
        
        users = load_users()
        users[str(query.from_user.id)] = {
            "plan": "free",
            "expiry": int(time.time()) + 24 * 3600
        }
        save_users(users)

        await query.message.reply_text(
            "🎉 Congratulations! You are verified for <b>24h Free Access</b>.\n\n"
            "👉 Enjoy InstaHub tools now!",
            parse_mode="HTML"
        )

    elif query.data == "premium":
        premium_text = (
            "💎 <b>Premium Plans</b>\n\n"
            "✨ 7 Days - ₹99\n"
            "✨ 30 Days - ₹299\n\n"
            "📌 Send payment screenshot to admin:\n"
            "@InstaHub_Admin"
        )
        await query.message.reply_text(premium_text, parse_mode="HTML")

# ----------------- EXPIRY -----------------
async def expiry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    users = load_users()
    user = users.get(str(update.effective_user.id))

    if not user or user["plan"] == "none":
        await update.message.reply_text("❌ You are not verified yet. Use /verify first.")
        return

    exp_time = user["expiry"]
    left = exp_time - int(time.time())

    if left <= 0:
        await update.message.reply_text("⚠️ Your plan has expired. Please verify again or buy Premium.")
    else:
        hours = left // 3600
        minutes = (left % 3600) // 60
        await update.message.reply_text(
            f"⏳ Your {user['plan']} plan will expire in {hours}h {minutes}m."
        )

# ----------------- POST (BROADCAST) -----------------
async def post_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ You are not allowed to use this command.")
        return
    
    if not context.args:
        await update.message.reply_text("Usage: /post Your message here")
        return
    
    text = " ".join(context.args)
    users = load_users()
    count = 0

    for user_id in users.keys():
        try:
            await context.bot.send_message(chat_id=int(user_id), text=text)
            count += 1
        except Exception:
            pass
    
    await update.message.reply_text(f"✅ Broadcast sent to {count} users.")

# ----------------- DASHBOARD -----------------
async def dashboard_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != OWNER_ID:
        await update.message.reply_text("❌ You are not allowed to use this command.")
        return

    users = load_users()
    total_users = len(users)
    verified_users = sum(1 for u in users.values() if u["plan"] == "free")
    premium_users = sum(1 for u in users.values() if u["plan"] == "premium")
    current_time = int(time.time())
    active_users = sum(1 for u in users.values() if u["expiry"] > current_time)

    msg = (
        "📊 <b>Dashboard</b>\n\n"
        f"👤 Total Users: <b>{total_users}</b>\n"
        f"✅ 24h Verified: <b>{verified_users}</b>\n"
        f"💎 Premium Users: <b>{premium_users}</b>\n"
        f"📅 Active Users: <b>{active_users}</b>"
    )

    await update.message.reply_text(msg, parse_mode="HTML")

# ----------------- MAIN -----------------
def main():
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CommandHandler("verify", start))
    application.add_handler(CommandHandler("expiry", expiry))
    application.add_handler(CommandHandler("post", post_handler))
    application.add_handler(CommandHandler("dashboard", dashboard_handler))

    application.run_polling()

if __name__ == "__main__":
    main()
