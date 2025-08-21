import logging
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters

# Logging enable kar dete hain (debugging ke liye)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Token (apna token yaha daalo)
TOKEN = "8125551108:AAFej9_9y9JieML31sjXEYFs217TddX3wmQ"

# Start command
def start(update, context):
    update.message.reply_text("Hello! ✅ Bot is running 24/7 on Railway 🚀")

# Echo message
def echo(update, context):
    update.message.reply_text(update.message.text)

def main():
    updater = Updater(TOKEN, use_context=True)
    dp = updater.dispatcher

    # Handlers
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, echo))

    # Start polling
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
