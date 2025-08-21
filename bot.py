from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    ContextTypes
)

# ===== CONFIG =====
BOT_TOKEN = "8125551108:AAFej9_9y9JieML31sjXEYFs217TddX3wmQ"   # yaha apna bot token daalo
CHANNEL_ID = -1002573368807    # tumhara channel ID
VIDEO_LINKS = {
    "302": "https://example.com/video302",
    "101": "https://example.com/video101"
}  # video IDs aur unke links ka mapping

# ===== CHECK CHANNEL JOIN =====
async def is_member(user_id: int, context: ContextTypes.DEFAULT_TYPE):
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# ===== /start handler =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    args = context.args

    if not args:
        await update.message.reply_text("❌ No video id provided.\n\nUsage: `/start v=302`",
                                        parse_mode="Markdown")
        return

    # Extract video id
    video_arg = args[0]
    if video_arg.startswith("v="):
        video_id = video_arg.split("=")[1]
    else:
        await update.message.reply_text("⚠️ Wrong format. Use `/start v=302`")
        return

    # Store video_id in user_data for later
    context.user_data["video_id"] = video_id

    # Check membership
    joined = await is_member(user_id, context)

    if not joined:
        # Send join message with buttons
        keyboard = [
            [InlineKeyboardButton("📢 Join Channel", url="https://t.me/parishram_2026_1_0")],
            [InlineKeyboardButton("✅ I Joined", callback_data="check_join")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(
            "⚠️ You must join our channel to get the video link.",
            reply_markup=reply_markup
        )
        return

    # If already joined, send link
    await send_video_link(update, context, video_id)

# ===== SEND VIDEO LINK =====
async def send_video_link(update: Update, context: ContextTypes.DEFAULT_TYPE, video_id: str):
    link = VIDEO_LINKS.get(video_id)
    if link:
        await update.message.reply_text(f"✅ Here is your video link:\n{link}")
    else:
        await update.message.reply_text("❌ Video not found.")

# ===== CALLBACK (I Joined button) =====
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "check_join":
        joined = await is_member(user_id, context)
        video_id = context.user_data.get("video_id")

        if joined and video_id:
            await query.edit_message_text("✅ Verified! Sending your link...")
            await context.bot.send_message(chat_id=user_id,
                                           text=f"🎬 Your requested video:\n{VIDEO_LINKS.get(video_id, '❌ Not found.')}")
        else:
            await query.edit_message_text("❌ You have not joined the channel yet.\nPlease join and press again.")

# ===== MAIN =====
def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))

    app.run_polling()

if __name__ == "__main__":
    main()
