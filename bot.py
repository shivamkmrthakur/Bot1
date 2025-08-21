from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext

# --- Your Bot Token (from BotFather) ---
BOT_TOKEN = "8125551108:AAFej9_9y9JieML31sjXEYFs217TddX3wmQ"

# --- Your channel username and URL ---
CHANNEL_USERNAME = "parishram_2026_1_0"
CHANNEL_URL = "https://t.me/parishram_2026_1_0"

# --- Store videos directly here ---
VIDEO_LINKS = {
    "302": "https://example.com/video302.mp4",
    "303": "https://example.com/video303.mp4",
    "304": "https://example.com/video304.mp4"
}

def start(update: Update, context: CallbackContext):
    args = context.args
    if not args:
        update.message.reply_text("Usage: /start?v=302")
        return

    video_id = args[0].replace("v=", "")
    user_id = update.effective_user.id

    # Check if user is in channel
    member = context.bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)

    if member.status in ["member", "administrator", "creator"]:
        link = VIDEO_LINKS.get(video_id)
        if link:
            update.message.reply_text(f"Here is your link: {link}")
        else:
            update.message.reply_text("Video not found in database.")
    else:
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("✅ Joined", callback_data=f"joined:{video_id}")]
        ])
        update.message.reply_text(
            f"Please join our channel first:\n{CHANNEL_URL}",
            reply_markup=keyboard
        )

def joined_callback(update: Update, context: CallbackContext):
    query = update.callback_query
    query.answer()
    video_id = query.data.split(":")[1]
    user_id = query.from_user.id

    # Re-check membership
    member = context.bot.get_chat_member(f"@{CHANNEL_USERNAME}", user_id)

    if member.status in ["member", "administrator", "creator"]:
        link = VIDEO_LINKS.get(video_id)
        if link:
            query.edit_message_text(f"Here is your link: {link}")
        else:
            query.edit_message_text("Video not found in database.")
    else:
        query.edit_message_text(f"You are still not in the channel! Join here: {CHANNEL_URL}")

def main():
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(joined_callback, pattern=r"^joined:"))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
