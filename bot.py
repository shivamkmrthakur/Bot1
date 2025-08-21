from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "8125551108:AAFej9_9y9JieML31sjXEYFs217TddX3wmQ"
CHANNEL_ID = -1002877068674 # yaha apna channel ka numeric ID daalna (not username)

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    video_id = None

    if text == "/start":
        await update.message.reply_text(
            "👉 Go to https://mission-catalyst.blogspot.com\n"
            "Select your class, subject, chapter, and lecture.\n"
            "Then click on *Watch Lecture* and then send me that lecture id like `/start 302`",
            parse_mode="Markdown"
        )
        return

    if "?v=" in text:
        video_id = text.split("?v=")[-1].strip()
    elif " " in text:
        video_id = text.split(" ", 1)[-1].strip()

    if not video_id:
        await update.message.reply_text("❌ No video id provided.\nUsage: /start 302 or /start?v=302")
        return

    context.user_data["video_id"] = video_id

    keyboard = [
        [InlineKeyboardButton("📢 Join Telegram Channel", url="https://t.me/parishram_2025_1_0")],
        [InlineKeyboardButton("🔔 Subscribe YouTube", url="https://www.youtube.com/@missioncatalyst")],
        [InlineKeyboardButton("✅ Joined", callback_data="joined")]
    ]
    await update.message.reply_text(
        "⚠️ Please join our *Telegram channel* and *Subscribe YouTube channel* first to get the lecture.",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# Handle Joined button
async def joined_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    video_id = context.user_data.get("video_id")

    if not video_id:
        await query.edit_message_text("❌ No video id found. Please use /start 302 again.")
        return

    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status in ["member", "administrator", "creator"]:
            # Agar Telegram join hai to ab YouTube subscribe check karne ka step
            keyboard = [
                [InlineKeyboardButton("🔔 Subscribe YouTube", url="https://www.youtube.com/@missioncatalyst")],
                [InlineKeyboardButton("✅ Subscribed", callback_data="subscribed")]
            ]
            await query.edit_message_text(
                "✅ You joined the Telegram channel!\n\n❌ But you are not subscribed to YouTube.\n\n"
                "👉 Please subscribe and then click *Subscribed*.",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.edit_message_text("❌ You have not joined the Telegram channel yet.")
    except:
        await query.edit_message_text("❌ Error checking channel membership.")


# Handle Subscribed button
async def subscribed_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    video_id = context.user_data.get("video_id")

    if not video_id:
        await query.edit_message_text("❌ No video id found. Please use /start 302 again.")
        return

    try:
        # Direct forward karega post ko
        await context.bot.forward_message(
            chat_id=user_id,
            from_chat_id=CHANNEL_ID,
            message_id=int(video_id)
        )
        await query.edit_message_text("✅ Here is your lecture:")
    except:
        await query.edit_message_text(f"❌ Post not found\nPost ID: {video_id}")


if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(joined_callback, pattern="joined"))
    app.add_handler(CallbackQueryHandler(subscribed_callback, pattern="subscribed"))

    print("Bot is running...")
    app.run_polling()
