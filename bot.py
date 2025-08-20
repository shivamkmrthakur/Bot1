from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# Yaha tumhara BotFather token direct diya hai
BOT_TOKEN = "8125551108:AAFej9_9y9JieML31sjXEYFs217TddX3wmQ"

# Apna source aur destination channel/group ID
SOURCE_CHAT_ID = -1001234567890   # yahan apne channel ka ID daalna
DEST_CHAT_ID = -1001234567890     # jahan forward karna hai (agar wahi hai to same rehne do)

# Mapping v parameter → message IDs
VIDEO_MAP = {
    "1": 5,
    "2": 7,
    "3": 10
    # aur bhi add kar sakte ho
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    if "?v=" in query:
        v_value = query.split("?v=")[-1]
        msg_id = VIDEO_MAP.get(v_value)
        if msg_id:
            try:
                await context.bot.forward_message(
                    chat_id=update.effective_chat.id,  # user ko bhej raha hu
                    from_chat_id=SOURCE_CHAT_ID,
                    message_id=msg_id
                )
                await update.message.reply_text(f"✅ Video v={v_value} forward ho gaya!")
            except Exception as e:
                await update.message.reply_text(f"⚠️ Error: {e}")
        else:
            await update.message.reply_text("❌ Galat v value di hai.")
    else:
        await update.message.reply_text("ℹ️ Use: /start?v=1")

if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()
