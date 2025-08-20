from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import re

# 🔹 BotFather token
BOT_TOKEN = "8125551108:AAFej9_9y9JieML31sjXEYFs217TddX3wmQ"

# 🔹 Correct channel ID (from @userinfobot)
SOURCE_CHAT_ID = -1002573368807   # Parishram 2026 Lectures

# 🔹 Mapping (optional: for /start?v=...)
VIDEO_MAP = {
    "100": 100,   # Example lecture
    "101": 101,
    "102": 102
}


# 🔹 Helper function to forward message
async def forward_video(context, msg_id, target_chat):
    try:
        await context.bot.forward_message(
            chat_id=target_chat,
            from_chat_id=SOURCE_CHAT_ID,
            message_id=msg_id
        )
        return True
    except Exception as e:
        await context.bot.send_message(chat_id=target_chat, text=f"⚠️ Forward error: {e}")
        return False


# 🔹 /start handler
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.message.text.strip()

    # Case 1: /start?v=100
    if "?v=" in query:
        v_value = query.split("?v=")[-1]
        msg_id = VIDEO_MAP.get(v_value)
        if msg_id:
            success = await forward_video(context, msg_id, update.effective_chat.id)
            if success:
                await update.message.reply_text(f"✅ Lecture v={v_value} forwarded.")
        else:
            await update.message.reply_text("❌ Galat v value di hai. Check VIDEO_MAP.")

    # Case 2: /start <telegram link>
    elif "t.me" in query:
        match = re.search(r"/(\d+)$", query)
        if match:
            msg_id = int(match.group(1))
            success = await forward_video(context, msg_id, update.effective_chat.id)
            if success:
                await update.message.reply_text(f"✅ Lecture (msg_id={msg_id}) forwarded.")
        else:
            await update.message.reply_text("❌ Could not extract message_id from link.")

    else:
        await update.message.reply_text(
            "ℹ️ Use:\n"
            "`/start?v=100` (with VIDEO_MAP)\n"
            "OR\n"
            "`/start https://t.me/parishram_2026_1_0/100`"
        )


# 🔹 Run bot
if __name__ == "__main__":
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()
