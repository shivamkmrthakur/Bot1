import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from urllib.parse import urlparse

# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Replace with your bot token
BOT_TOKEN = "YOUR_BOT_TOKEN"

# Source and destination chat IDs
SOURCE_CHAT_ID = -1002573368807   # Parishram 2026 Lectures channel
DEST_CHAT_ID = "me"              # "me" means your Saved Messages

# ----------- START ------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("❌ Usage: /start <lecture_link>")
        return

    link = context.args[0]
    try:
        parsed = urlparse(link)
        msg_id = int(parsed.path.strip("/").split("/")[-1])

        await context.bot.forward_message(
            chat_id=DEST_CHAT_ID,
            from_chat_id=SOURCE_CHAT_ID,
            message_id=msg_id
        )

        await update.message.reply_text("✅ Lecture forwarded to Saved Messages!")

    except Exception as e:
        await update.message.reply_text(f"⚠️ Forward error: {e}")

# ----------- CHECK ------------
async def check_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check if bot can access source channel"""
    try:
        chat = await context.bot.get_chat(SOURCE_CHAT_ID)
        await update.message.reply_text(f"✅ Bot can access: {chat.title}")
    except Exception as e:
        await update.message.reply_text(f"❌ Error: {e}")

# ----------- MAIN ------------
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("check", check_chat))

    app.run_polling()

if __name__ == "__main__":
    main()
