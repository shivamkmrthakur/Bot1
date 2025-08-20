import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from telegram.error import Forbidden

# --- CONFIGURATION ---
BOT_TOKEN = "8125551108:AAFej9_9y9JieML31sjXEYFs217TddX3wmQ"
CHANNEL_ID = -1002371985459  # Your channel ID

# Map video ID (?v=1, ?v=2, etc.) to Telegram message IDs
VIDEO_MAP = {
    "1": 5,   # ?v=1 → forward msg_id 5
    "2": 7,   # ?v=2 → forward msg_id 7
    "3": 10,  # ?v=3 → forward msg_id 10
}

# --- LOGGING ---
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    args = context.args

    if not args:
        await update.message.reply_text("Usage: /start v=1")
        return

    query = args[0]  # e.g. v=1
    if not query.startswith("v="):
        await update.message.reply_text("Invalid format. Use /start v=1")
        return

    vid_id = query.split("=")[1]
    msg_id = VIDEO_MAP.get(vid_id)

    if not msg_id:
        await update.message.reply_text("❌ Video not found.")
        return

    # Check if user is in channel
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user.id)
        if member.status in ["left", "kicked"]:
            join_link = f"https://t.me/{str(CHANNEL_ID)[4:]}"  # public channel username if available
            await update.message.reply_text(
                f"🚨 Please join the channel first:\n👉 {join_link}"
            )
            return
    except Forbidden:
        await update.message.reply_text("⚠️ Bot is not admin in the channel. Please fix that.")
        return

    # Forward the video
    try:
        await context.bot.forward_message(
            chat_id=update.effective_chat.id,
            from_chat_id=CHANNEL_ID,
            message_id=msg_id
        )
    except Exception as e:
        logger.error(f"Error forwarding message: {e}")
        await update.message.reply_text("⚠️ Could not forward the video.")


def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    print("✅ Bot started...")
    app.run_polling()


if __name__ == "__main__":
    main()

