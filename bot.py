from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Bot ka token
TOKEN = "8125551108:AAFej9_9y9JieML31sjXEYFs217TddX3wmQ"

# Channel IDs
CHANNEL_ID = -1002877068674       # Join check ke liye channel
SOURCE_CHANNEL_ID = -1002066954690  # Jaha se video forward hoga

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    video_id = None

    # Agar sirf /start bheja gaya
    if text == "/start":
        await update.message.reply_text(
            "👉 Go to https://mission-catalyst.blogspot.com\n"
            "Select your class, subject, chapter, and lecture.\n"
            "Then click on *Watch Lecture* and send me that lecture id like:\n\n"
            "`/start 302`\n\n"
            "⚠️ Example: Agar video ka message ID 104 hai to aap likhen `/start 104`",
            parse_mode="Markdown"
        )
        return

    # Agar ?v= style id bheja ho
    if "?v=" in text:
        video_id = text.split("?v=")[-1].strip()
    # Agar space ke sath id bheja ho (/start 104)
    elif " " in text:
        video_id = text.split(" ", 1)[-1].strip()

    # Agar id nahi mili
    if not video_id or not video_id.isdigit():
        await update.message.reply_text(
            "❌ Invalid video id.\nUsage: `/start 302`\n\n⚠️ Example: `/start 104`",
            parse_mode="Markdown"
        )
        return

    # Save user video id
    context.user_data["video_id"] = video_id

    # Ask to join channel + subscribe
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
        # Forward from source channel
        await context.bot.forward_message(
            chat_id=user_id,
            from_chat_id=SOURCE_CHANNEL_ID,
            message_id=int(video_id)
        )
        await query.edit_message_text("✅ Here is your lecture:")
    except Exception as e:
        await query.edit_message_text(f"❌ Post not found\nPost ID: {video_id}\nError: {e}")


if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(joined_callback, pattern="joined"))
    app.add_handler(CallbackQueryHandler(subscribed_callback, pattern="subscribed"))

    print("Bot is running...")
    app.run_polling()
