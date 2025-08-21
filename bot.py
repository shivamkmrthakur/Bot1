from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "8125551108:AAFej9_9y9JieML31sjXEYFs217TddX3wmQ"
CHANNEL_ID = "-1002573368807"  # apna channel id

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    args = context.args

    if not args:
        await update.message.reply_text("❌ No video id provided.\nUsage: /start 302 or /start?v=302")
        return

    # handle both /start 302 and /start?v=302
    video_id = args[0].replace("v=", "")
    user_id = update.effective_user.id

    # Check membership
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status in ["member", "administrator", "creator"]:
            await update.message.reply_text(
                f"✅ You are a member!\nHere is your requested link:\n👉 https://example.com/video/{video_id}"
            )
        else:
            await send_join_message(update)
    except:
        await send_join_message(update)


# Send join message
async def send_join_message(update: Update):
    keyboard = [
        [InlineKeyboardButton("📢 Join Channel", url="https://t.me/parishram_2026_1_0")],
        [InlineKeyboardButton("✅ Joined", callback_data="joined")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("⚠️ Please join the channel first.", reply_markup=reply_markup)


# Handle "Joined" button
async def joined_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status in ["member", "administrator", "creator"]:
            await query.edit_message_text("✅ Thanks for joining!\nNow send /start 302 again to get your link.")
        else:
            await query.edit_message_text("❌ You have not joined the channel yet.")
    except:
        await query.edit_message_text("❌ Error checking channel membership.")


if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(joined_callback, pattern="joined"))

    print("Bot is running...")
    app.run_polling()
