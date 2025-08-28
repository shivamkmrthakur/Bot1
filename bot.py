#!/usr/bin/env python3
# bot.py

import os
import logging
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes
)

# ----------------- CONFIG -----------------
TOKEN = "PUT-YOUR-BOT-TOKEN-HERE"   # <-- apna token yaha daalna
OWNER_ID = 7347144999               # Apna Telegram ID
CHANNEL_NAME = "InstaHub"
CHANNEL_LINK = "https://t.me/Instaa_hubb"

# ----------------- LOGGING -----------------
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# ----------------- DATABASE (In-Memory) -----------------
users_db = {}  # { user_id: {"plan": "free/premium", "expiry": datetime} }

# ----------------- START -----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("✅ Verify Access", callback_data="verify")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        f"👋 *Welcome to {CHANNEL_NAME} Bot!*\n\n"
        "🚀 Your personal tool to request InstaHub videos anytime, anywhere.\n\n"
        "👉 Click below to *verify your access* and get started.",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# ----------------- VERIFY -----------------
async def verify_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    expiry_time = datetime.now() + timedelta(hours=24)
    users_db[user.id] = {"plan": "free", "expiry": expiry_time}

    keyboard = [[InlineKeyboardButton("💎 Upgrade to Premium", callback_data="get_premium")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.callback_query.message.reply_text(
        "🎉 *Verification Successful!* 🎉\n\n"
        "✅ You now have *Free Access* valid for the next *24 hours*.\n\n"
        "✨ With this access you can:\n"
        "• Request InstaHub videos 📥\n"
        "• Enjoy a smooth experience 🚀\n\n"
        f"👉 Start now at [{CHANNEL_NAME}]({CHANNEL_LINK})\n\n"
        "💡 Want *Unlimited Access* with no expiry? Tap below and upgrade to *Premium*!",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# ----------------- PREMIUM WELCOME -----------------
async def premium_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    users_db[user_id] = {"plan": "premium", "expiry": datetime.now() + timedelta(days=30)}

    keyboard = [[InlineKeyboardButton("💎 Extend Premium", callback_data="get_premium")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "💎 *Welcome, Premium Member!* 💎\n\n"
        "✅ Your account has been upgraded to *Full Access*.\n\n"
        "✨ Benefits of Premium:\n"
        "• Unlimited InstaHub requests 📥\n"
        "• Ad-free & smooth usage 🚀\n"
        "• Longer validity 🕒\n\n"
        f"👉 Start enjoying all features now at [{CHANNEL_NAME}]({CHANNEL_LINK})",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# ----------------- EXPIRY -----------------
async def expiry(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    if user_id not in users_db:
        await update.message.reply_text(
            "⚠️ You don’t have any active plan yet.\n\n"
            "👉 Please use /start to verify your access."
        )
        return

    plan = users_db[user_id]["plan"]
    expiry_time = users_db[user_id]["expiry"]

    remaining = expiry_time - datetime.now()
    if remaining.total_seconds() <= 0:
        await update.message.reply_text(
            "❌ Your current plan has expired!\n\n"
            "💡 Upgrade now to *Premium* and continue enjoying InstaHub without limits.",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="get_premium")]
            ])
        )
        return

    days, seconds = remaining.days, remaining.seconds
    hours, minutes = seconds // 3600, (seconds % 3600) // 60

    await update.message.reply_text(
        "📅 *Your Plan Details* 📅\n\n"
        f"👤 User: `{update.effective_user.first_name}`\n"
        f"🆔 ID: `{update.effective_user.id}`\n\n"
        f"📌 Plan: *{plan.title()}*\n"
        f"⏳ Time Left: {days}d {hours}h {minutes}m\n"
        f"🕒 Expiry Date: {expiry_time.strftime('%d-%b-%Y | %I:%M %p')}\n\n"
        "✨ Upgrade to *Premium* for Unlimited Access 💎\n\n"
        f"👉 Visit [{CHANNEL_NAME}]({CHANNEL_LINK})",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("💎 Upgrade to Premium", callback_data="get_premium")]
        ])
    )

# ----------------- PREMIUM PLANS -----------------
async def premium_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query

    keyboard = [[InlineKeyboardButton("📤 Send Payment Screenshot", callback_data="send_screenshot")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.message.reply_text(
        "💎 *Premium Plans* 💎\n\n"
        "1️⃣ 7 Days – ₹XXX\n"
        "2️⃣ 30 Days – ₹XXX\n"
        "3️⃣ Lifetime – ₹XXX\n\n"
        "📌 To activate Premium:\n"
        "1. Complete payment via UPI/Number.\n"
        "2. Click below to *send your payment screenshot*.\n"
        "3. We will verify & upgrade your account shortly ✅",
        parse_mode="Markdown",
        reply_markup=reply_markup
    )

# ----------------- CALLBACK HANDLER -----------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "verify":
        await verify_user(update, context)
    elif query.data == "get_premium":
        await premium_plans(update, context)
    elif query.data == "send_screenshot":
        await query.message.reply_text(
            "📤 Please *send your payment screenshot* here.\n\n"
            "✅ Our team will review it and upgrade your account.",
            parse_mode="Markdown"
        )

# ----------------- MAIN -----------------
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("expiry", expiry))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
