from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# 🔑 Bot Token
BOT_TOKEN = "8125551108:AAFej9_9y9JieML31sjXEYFs217TddX3wmQ"

# 📢 Channel username (without https://t.me/)
CHANNEL_USERNAME = "@parishram_2026_1_0"

# 🟢 Check if user is member of channel
async def is_member(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(CHANNEL_USERNAME, user_id)
        return member.status in ["member", "administrator", "creator"]
    except Exception as e:
        print(f"Membership check error: {e}")
        return False

# 🟢 Start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    # Video ID निकालना
    video_id = None
    if context.args:  # /start 302
        video_id = context.args[0]
    elif update.message.text and "?v=" in update.message.text:  # /start?v=302
        video_id = update.message.text.split("?v=")[-1]

    if not video_id:
        await update.message.reply_text("❌ No video id provided.\nUsage: `/start 302` or `/start?v=302`", parse_mode="Markdown")
        return

    # Membership check
    if await is_member(user_id, context):
        await update.message.reply_text(f"🎬 Here is your requested video link:\n👉 https://example.com/video/{video_id}")
    else:
        keyboard = [
            [InlineKeyboardButton("📢 Join Channel", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
            [InlineKeyboardButton("✅ Joined", callback_data=f"joined_{video_id}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("⚠️ Please join our channel first to access the video.", reply_markup=reply_markup)

# 🟢 Handle "Joined ✅" button
async def joined(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    video_id = query.data.split("_")[1]

    if await is_member(user_id, context):
        await query.edit_message_text(f"🎬 Thanks for joining!\nHere is your video link:\n👉 https://example.com/video/{video_id}")
    else:
        await query.answer("❌ You are not a member yet!", show_alert=True)

# 🟢 Main Function
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(joined, pattern="^joined_"))

    print("✅ Bot started...")
    app.run_polling()

if __name__ == "__main__":
    main()
