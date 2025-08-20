from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# BotFather ka token
BOT_TOKEN = "8125551108:AAFej9_9y9JieML31sjXEYFs217TddX3wmQ"

# Source channel/group ID (jahan se video uthana hai)
SOURCE_CHAT_ID = -1002573368807   # Parishram 2026 Lectures

# Mapping v parameter → message IDs
VIDEO_MAP = {
    "1": 5,
    "2": 7,
    "3": 10
    # aur bhi add kar sakte ho
}

# 🔹 Helper function: forward video by v-value
async def forward_video(context: ContextTypes.DEFAULT_TYPE, v_value: str, target_chat: int):
    msg_id = VIDEO_MAP.get(v_value)
    if msg_id:
        await context.bot.forward_message(
            chat_id=target_chat,
            from_chat_id=SOURCE_CHAT_ID,
            message_id=msg_id
        )
        return True
    return False

# 🔹 /start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text
    if "?v=" in query:
        v_value = query.split("?v=")[-1]
        success = await forward_video(context, v_value, update.effective_chat.id)  # user ko bhejega
        if success:
            await update.message.reply_text(f"✅ Video v={v_value} forward ho gaya!")
        else:
            await update.message.reply_text("❌ Galat v value di hai.")
    else:
        await update.message.reply_text("ℹ️ Use: /start?v=1")

if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()
