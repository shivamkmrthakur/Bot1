import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# ✅ Your bot token
TOKEN = "8125551108:AAFej9_9y9JieML31sjXEYFs217TddX3wmQ"

# ✅ Your channel/group chat id
CHANNEL_ID = "-1002371985459"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 Bot is running! Send ?v=videoid to forward.")

# Forward command (?v=123)
async def forward_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if text.startswith("?v="):
        video_id = text.split("=")[-1]
        await context.bot.send_message(
            chat_id=CHANNEL_ID,
            text=f"Forwarding video with ID: {video_id}"
        )
        await update.message.reply_text("✅ Video forwarded to channel.")
    else:
        await update.message.reply_text("❌ Use format ?v=videoid")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("forward", forward_video))
    app.run_polling()

if __name__ == "__main__":
    main()
