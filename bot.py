from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from datetime import datetime

TOKEN = "8125551108:AAFej9_9y9JieML31sjXEYFs217TddX3wmQ"

# user की last join prompt दिखाने की तारीख store करने के लिए dict
user_last_prompt = {}

# Channel link
CHANNEL_LINK = "https://t.me/parishram_2026_1_0"


# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    video_id = None

    if "?v=" in text:
        video_id = text.split("?v=")[-1].strip()
    elif " " in text:
        video_id = text.split(" ", 1)[-1].strip()

    if not video_id:
        await update.message.reply_text(
            "❌ No video id provided.\nUsage: /start 302  or  /start?v=302"
        )
        return

    user_id = update.effective_user.id
    today = datetime.now().date()

    # Check अगर आज का join message पहले show नहीं हुआ
    if user_id not in user_last_prompt or user_last_prompt[user_id] != today:
        # पहली बार आज join message show करो
        user_last_prompt[user_id] = today
        await send_join_message(update, video_id)
    else:
        # उसी दिन दुबारा request → direct link भेजो
        await send_video_link(update, video_id)


# Send join message
async def send_join_message(update: Update, video_id: str):
    keyboard = [
        [InlineKeyboardButton("📢 Join Channel", url=CHANNEL_LINK)],
        [InlineKeyboardButton("✅ Joined", callback_data=f"joined:{video_id}")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "⚠️ Please join the channel first.", reply_markup=reply_markup
    )


# Send video link
async def send_video_link(update_or_query, video_id: str):
    link = f"https://example.com/video/{video_id}"

    if isinstance(update_or_query, Update):
        await update_or_query.message.reply_text(
            f"✅ Here is your requested link:\n👉 {link}"
        )
    else:
        await update_or_query.edit_message_text(
            f"✅ Here is your requested link:\n👉 {link}"
        )


# Handle "Joined" button
async def joined_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    data = query.data
    if data.startswith("joined:"):
        video_id = data.split("joined:")[-1]
        await send_video_link(query, video_id)


if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(joined_callback, pattern="joined:"))

    print("Bot is running...")
    app.run_polling()
