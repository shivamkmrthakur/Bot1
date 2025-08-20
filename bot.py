import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Get bot token from Railway Environment Variable
TOKEN = os.getenv("BOT_TOKEN")

# Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hello! ✅ Bot is running successfully on Railway.")

# Echo command (replies with whatever you send)
async def echo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(update.message.text)

def main():
    app = Application.builder().token(TOKEN).build()

    # Commands
    app.add_handler(CommandHandler("start", start))

    # Messages
    app.add_handler(CommandHandler("echo", echo))

    print("✅ Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
