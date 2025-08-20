from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import re

# 🔹 BotFather token
BOT_TOKEN = "YOUR_BOT_TOKEN_HERE"

# 🔹 Source channel ID
SOURCE_CHAT_ID = -1002573368807   # Parishram 2026 Lectures

# 🔹 /start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()

    # Case 1: /start?v=1 type (old method with VIDEO_MAP)
    if "?v=" in query:
        v_value = query.split("?v=")[-1]
        VIDEO_MAP = {
            "1": 100,   # you can still keep static IDs
            "2": 101,
            "3": 102
        }
        msg_id = VIDEO_MAP.get(v_value)
        if msg_id:
            try:
                await context.bot.forward_message(
                    chat_id=update.effective_chat.id,
                    from_chat_id=SOURCE_CHAT_ID,
                    message_id=msg_id
                )
                await update.message.reply_text(f"✅ Forwarded video v={v_value}")
            except Exception as e:
                await update.message.reply_text(f"⚠️ Error: {e}")
        else:
            await update.message.reply_text("❌ Invalid v value.")

    # Case 2: User gives full Telegram link
    elif "t.me" in query:
        match = re.search(r"/(\d+)$", query)
        if match:
            msg_id = int(match.group(1))
            try:
                await context.bot.forward_message(
                    chat_id=update.effective_chat.id,
                    from_chat_id=SOURCE_CHAT_ID,
                    message_id=msg_id
                )
                await update.message.reply_text(f"✅ Forwarded from link (msg_id={msg_id})")
            except Exception as e:
                await update.message.reply_text(f"⚠️ Error: {e}")
        else:
            await update.message.reply_text("❌ Could not extract message_id from link.")

    else:
        await update.message.reply_text("ℹ️ Use: /start?v=1 or paste Telegram post link.")

# 🔹 Run bot
if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()
