from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import os

TOKEN = "8125551108:AAFej9_9y9JieML31sjXEYFs217TddX3wmQ"
CHANNEL_ID = -1002877068674 # yaha apna channel ka numeric ID daalna (not username)

# /start command
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    video_id = None

    if "?v=" in text:
        video_id = text.split("?v=")[-1].strip()
    elif " " in text:
        video_id = text.split(" ", 1)[-1].strip()

    if not video_id:
        await update.message.reply_text("❌ No video id provided.\nUsage: /start 302  or  /start?v=302")
        return

    # Save user video id in context (so we can forward later after join check)
    context.user_data["video_id"] = video_id

    keyboard = [
        [InlineKeyboardButton("📢 Join Channel", url="https://t.me/parishram_2025_1_0")],
        [InlineKeyboardButton("✅ Joined", callback_data="joined")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "⚠️ Please join the channel first to get the lecture.",
        reply_markup=reply_markup
    )

# Joined button handler
async def joined_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    video_id = context.user_data.get("video_id")

    if not video_id:
        await query.edit_message_text("❌ No video id found. Please use /start 302 again.")
        return

    try:
        # Check membership
        member = await context.bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status in ["member", "administrator", "creator"]:
            # Forward the post
            try:
                await context.bot.forward_message(
                    chat_id=user_id,
                    from_chat_id=CHANNEL_ID,
                    message_id=int(video_id)
                )
                await query.edit_message_text("✅ Here is your lecture:")
            except:
                await query.edit_message_text(f"❌ Post not found\nPost ID: {video_id}")
        else:
            await query.edit_message_text("❌ You have not joined the channel yet.")
    except:
        await query.edit_message_text("❌ Error checking channel membership.")


if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(joined_callback, pattern="joined"))

    print("Bot is running...")
    app.run_polling()
