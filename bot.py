from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ Bot is running successfully!")

def main():
    # Create Application
    app = Application.builder().token("8125551108:AAFej9_9y9JieML31sjXEYFs217TddX3wmQ").build()

    # Add command handler
    app.add_handler(CommandHandler("start", start))

    # Run bot
    app.run_polling()

if __name__ == "__main__":
    main()
