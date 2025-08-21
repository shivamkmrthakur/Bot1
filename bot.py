from telegram import Update, InlineKeyboardMarkup, InlineKeyboardButton
from telegram.ext import Application, CommandHandler, ContextTypes

BOT_TOKEN = "8125551108:AAFej9_9y9JieML31sjXEYFs217TddX3wmQ"
CHANNEL_ID = -1002573368807   # apna channel id

VIDEO_LINKS = {
    "302": "https://example.com/video302.mp4",
    "303": "https://example.com/video303.mp4"
}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()  # full command text lelo
    
    video_id = None
    if "?v=" in text:   # agar /start?v=302 format hai
        try:
            video_id = text.split("?v=")[1]
        except:
            video_id = None
    elif len(context.args) > 0:  # agar /start 302 format hai
        video_id = context.args[0]

    if not video_id:
        await update.message.reply_text("❌ No video id provided.\nUsage:\n/start?v=302 or /start 302")
        return

    if video_id not in VIDEO_LINKS:
        await update.message.reply_text("❌ Invalid video id.")
        return

    user_id = update.effective_user.id

    # Check if user is in channel
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status in ["member", "administrator", "creator"]:
            await update.message.reply_text(f"✅ Here is your link:\n{VIDEO_LINKS[video_id]}")
        else:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("👉 Join Channel", url="https://t.me/parishram_2026_1_0")],
                [InlineKeyboardButton("✅ I Joined", callback_data=f"joined_{video_id}")]
            ])
            await update.message.reply_text("⚠️ Please join the channel to get the link.", reply_markup=keyboard)
    except:
        await update.message.reply_text("⚠️ Please join the channel first.")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()

if __name__ == "__main__":
    main()
