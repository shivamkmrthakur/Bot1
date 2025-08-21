from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import datetime

TOKEN = "8125551108:AAFej9_9y9JieML31sjXEYFs217TddX3wmQ"

# store user last served date + video_id
user_data = {}

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text  # full message e.g. "/start?v=302"
    video_id = None

    if "?v=" in text:
        video_id = text.split("?v=")[-1].strip()
    elif " " in text:
        video_id = text.split(" ", 1)[-1].strip()

    if not video_id:
        await update.message.reply_text("❌ No video id provided.\nUsage: /start 302  or  /start?v=302")
        return

    user_id = update.effective_user.id
    today = datetime.date.today()

    # Check if already served today
    if user_id in user_data and user_data[user_id]["date"] == today:
        await update.message.reply_text(
            f"🎬 Here is your requested video link again:\n👉 https://example.com/video/{user_data[user_id]['video_id']}"
        )
        return

    # Directly send video link
    await send_video_link(update, video_id, user_id)


# Send video link + store data
async def send_video_link(update_or_query, video_id: str, user_id: int):
    today = datetime.date.today()
    user_data[user_id] = {"date": today, "video_id": video_id}

    # If it's from query button
    if hasattr(update_or_query, "edit_message_text"):
        await update_or_query.edit_message_text(
            f"✅ Here is your requested link:\n👉 https://example.com/video/{video_id}"
        )
    else:
        # Normal /start msg
        await update_or_query.message.reply_text(
            f"✅ Here is your requested link:\n👉 https://example.com/video/{video_id}"
        )


# Handle "Joined" button
async def joined_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    video_id = query.data.split("_")[1]

    await send_video_link(query, video_id, user_id)


if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(joined_callback, pattern="^joined_"))

    print("✅ Bot is running...")
    app.run_polling()
