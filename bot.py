from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import datetime

TOKEN = "8125551108:AAFej9_9y9JieML31sjXEYFs217TddX3wmQ"

# Links
CHANNEL_ID = -1002573368807   # apna channel ka numeric ID (yeh zaroori hai)
CHANNEL_LINK = "https://t.me/parishram_2025_1_0"
YOUTUBE_LINK = "https://www.youtube.com/@missioncatalyst"
BLOG_LINK = "https://mission-catalyst.blogspot.com"

# Store user daily join status
user_last_date = {}


# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text  # e.g. "/start?v=302"
    video_id = None

    if "?v=" in text:
        video_id = text.split("?v=")[-1].strip()
    elif " " in text:
        video_id = text.split(" ", 1)[-1].strip()

    user_id = update.effective_user.id
    today = datetime.now().date()

    # If only /start (no video id)
    if not video_id:
        keyboard = [
            [InlineKeyboardButton("📢 Join Telegram Channel", url=CHANNEL_LINK)],
            [InlineKeyboardButton("▶️ Subscribe YouTube", url=YOUTUBE_LINK)],
            [InlineKeyboardButton("✅ Done", callback_data="done")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "⚠️ Please join our Telegram channel and subscribe our YouTube channel first.",
            reply_markup=reply_markup
        )
        return

    # If video id is given
    if user_last_date.get(user_id) != today:
        # First time today → show join message
        keyboard = [
            [InlineKeyboardButton("📢 Join Telegram Channel", url=CHANNEL_LINK)],
            [InlineKeyboardButton("▶️ Subscribe YouTube", url=YOUTUBE_LINK)],
            [InlineKeyboardButton("✅ Done", callback_data=f"video_{video_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "⚠️ Please join our Telegram channel and subscribe our YouTube channel first.",
            reply_markup=reply_markup
        )
    else:
        # Already verified today → directly forward post
        await forward_post(update, context, video_id)


# Forward channel post
async def forward_post(update: Update, context: ContextTypes.DEFAULT_TYPE, video_id: str):
    try:
        await context.bot.forward_message(
            chat_id=update.effective_chat.id,  # user ko bhejna hai
            from_chat_id=CHANNEL_ID,           # apna channel
            message_id=int(video_id)           # post ka message_id
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}\n\nPost ID: {video_id}")


# Handle Done button
async def done_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data.startswith("video_"):
        video_id = query.data.split("_")[1]
        user_last_date[user_id] = datetime.now().date()

        # Forward post instead of link
        try:
            await context.bot.forward_message(
                chat_id=query.message.chat.id,
                from_chat_id=CHANNEL_ID,
                message_id=int(video_id)
            )
            await query.edit_message_text("✅ Here is your requested lecture 👇")
        except Exception as e:
            await query.edit_message_text(f"❌ Error forwarding post: {e}")
    else:
        await query.edit_message_text(
            f"✅ Great! Now follow this:\n\n👉 Go to {BLOG_LINK}\nSelect your class, subject, chapter, and lecture.\nThen send me `/start 302`"
        )


if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(done_callback))

    print("Bot is running...")
    app.run_polling()
