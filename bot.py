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
SOURCE_CHANNEL = "@instahubackup"  
SOURCE_CHANNEL_2 = "@instahubackup2"
JOIN_CHANNELS = [SOURCE_CHANNEL, SOURCE_CHANNEL_2]

# ----------------- DATABASE -----------------
users_db = {}

# ----------------- HANDLERS -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("✅ Verify Now", callback_data="verify")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "👋 Welcome to [InstaHub](https://t.me/Instaa_hubb)!\n\n"
        "🔹 To continue, please verify your account by joining our required channels.\n"
        "⏳ You’ll then get **24 hours free access**.\n\n"
        "💎 Want unlimited access? Upgrade to Premium anytime!",
        reply_markup=reply_markup,
        disable_web_page_preview=True
    )

async def verify_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id

    # check if user joined all channels
    for ch in JOIN_CHANNELS:
        member = await context.bot.get_chat_member(ch, user_id)
        if member.status not in ["member", "administrator", "creator"]:
            keyboard = [[InlineKeyboardButton("📌 Join Channels", url=f"https://t.me/{ch[1:]}")]]
            await query.message.reply_text(
                "⚠️ You must join all required channels first!\n\n"
                f"👉 Please join: {', '.join(JOIN_CHANNELS)}\n"
                "Then press Verify again ✅",
                reply_markup=InlineKeyboardMarkup(keyboard),
                disable_web_page_preview=True
            )
            return

    # set free 24h access
    expiry = int(time.time()) + 24 * 3600
    users_db[user_id] = {"plan": "Free (24h)", "expiry": expiry}

    keyboard = [
        [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="plans")],
        [InlineKeyboardButton("🚀 Open InstaHub", url="https://t.me/Instaa_hubb")]
    ]
    await query.message.reply_text(
        "🎉 Congratulations! You are now verified for **24 hours free access**.\n\n"
        "👉 Start exploring videos on [InstaHub](https://t.me/Instaa_hubb).\n\n"
        "💡 Tip: Upgrade to Premium for **unlimited, ad-free access**!",
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True
    )

async def plans_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    keyboard = [[InlineKeyboardButton("📤 Send Screenshot", callback_data="screenshot")]]
    await query.message.reply_text(
        "💎 *Premium Plans*\n\n"
        "🔹 1 Month – ₹99\n"
        "🔹 3 Months – ₹249\n"
        "🔹 Lifetime – ₹499\n\n"
        "📌 Pay via UPI: `instahub@upi`\n"
        "📤 After payment, send a screenshot to verify.",
        reply_markup=InlineKeyboardMarkup(keyboard),
        disable_web_page_preview=True,
        parse_mode="Markdown"
    )

async def screenshot_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.message.reply_text(
        "📸 Please upload your payment screenshot here.\n\n"
        "Our team will verify and upgrade you to Premium within 30 minutes ✅"
    )

async def expiry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    user = users_db.get(user_id)

    if not user:
        await update.message.reply_text(
            "⚠️ You don’t have an active plan.\n\n"
            "👉 Please verify first or upgrade to Premium.",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💎 Upgrade", callback_data="plans")]])
        )
        return

    remaining = int(user["expiry"] - time.time())
    if remaining <= 0:
        await update.message.reply_text(
            "⏳ Your free plan has expired.\n\n"
            "💎 Upgrade to Premium for unlimited access!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Upgrade Now", callback_data="plans")]])
        )
        return

    hours = remaining // 3600
    minutes = (remaining % 3600) // 60
    await update.message.reply_text(
        f"🕒 Your current plan: *{user['plan']}*\n"
        f"⏳ Time left: {hours}h {minutes}m\n\n"
        "💡 Upgrade anytime for **full Premium access**!",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("💎 Upgrade", callback_data="plans")]]),
        parse_mode="Markdown"
    )

# ----------------- MAIN -----------------
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("expiry", expiry))
    app.add_handler(CallbackQueryHandler(verify_callback, pattern="verify"))
    app.add_handler(CallbackQueryHandler(plans_callback, pattern="plans"))
    app.add_handler(CallbackQueryHandler(screenshot_callback, pattern="screenshot"))

    print("✅ Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
