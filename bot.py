import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, CallbackContext
import requests

# Your bot token
BOT_TOKEN = "PUT_YOUR_NEW_TOKEN_HERE"

# Your channel username (without https://t.me/)
CHANNEL_USERNAME = "parishram_2026_1_0"

# Store video IDs and links here
video_links = {
    "302": "https://example.com/video302",
    "303": "https://example.com/video303",
    "304": "https://example.com/video304"
}

# Enable logs (for Railway)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)

# Function to check if user is member of channel
def is_user_member(user_id):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getChatMember?chat_id=@{CHANNEL_USERNAME}&user_id={user_id}"
    resp = requests.get(url).json()
    status = resp.get("result", {}).get("status", "")
    return status in ["member", "administrator", "creator"]

# /start command
def start(update: Update, context: CallbackContext):
    args = context.args
    user_id = update.effective_user.id

    if not args:
        update.message.reply_text("❌ Invalid link. Use a proper start link.")
        return

    video_id = args[0].replace("v=", "") if args[0].startswith("v=") else args[0]

    if video_id not in video_links:
        update.message.reply_text("❌ Video not found.")
        return

    if is_user_member(user_id):
        update.message.reply_text(f"🎬 Here is your video link:\n{video_links[video_id]}")
    else:
        # Ask user to join channel
        keyboard = [
            [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME}")],
            [InlineKeyboardButton("✅ I Joined", callback_data=f"joined_{video_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(
            "🚨 You must join our channel to get the link!",
            reply_markup=reply_markup
        )

# Handle button "I Joined"
def joined(update: Update, context: CallbackContext):
    query = update.callback_query
    user_id = query.from_user.id
    query.answer()

    video_id = query.data.split("_")[1]

    if is_user_member(user_id):
        query.edit_message_text(f"🎬 Here is your video link:\n{video_links[video_id]}")
    else:
        query.answer("❌ You have not joined yet!", show_alert=True)

# Main
if __name__ == "__main__":
    updater = Updater(BOT_TOKEN, use_context=True)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CallbackQueryHandler(joined, pattern="^joined_"))

    updater.start_polling()
    updater.idle()
