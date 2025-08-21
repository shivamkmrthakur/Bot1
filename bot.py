from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = "8125551108:AAFej9_9y9JieML31sjXEYFs217TddX3wmQ"

# Channel IDs
CHANNEL_JOIN_ID = -1002877068674      # jisme user ko join karna hai (@parishram_2025_1_0)
CHANNEL_FORWARD_ID = -1002573368807   # jisme se video forward karna hai (bot admin hona chahiye)

# ---------------- Commands ----------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    video_id = None

    if "?v=" in text:
        video_id = text.split("?v=")[-1].strip()
    elif " " in text:
        video_id = text.split(" ", 1)[-1].strip()

    if not video_id:
        await update.message.reply_text(
            "❌ No video id provided.\nUsage: /start 302  or  /start?v=302"
        )
        return

    context.user_data["video_id"] = video_id

    # Pehle blogspot ka msg bhejo
    msg = (
        "👉 Go to https://mission-catalyst.blogspot.com\n"
        "Select your class, subject, chapter, and lecture.\n"
        "Then click on *Watch Lecture* and I will share the lecture."
    )

    # Join button
    keyboard = [
        [InlineKeyboardButton("📢 Join Channel", url="https://t.me/parishram_2025_1_0")],
        [InlineKeyboardButton("✅ Joined", callback_data="joined")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(msg, reply_markup=reply_markup)


# ---------------- Step 1: Joined ----------------
async def joined_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    try:
        member = await context.bot.get_chat_member(CHANNEL_JOIN_ID, user_id)
        if member.status in ["member", "administrator", "creator"]:
            # Send YouTube subscribe step
            keyboard = [
                [InlineKeyboardButton("▶️ Subscribe YouTube", url="https://www.youtube.com/@missioncatalyst")],
                [InlineKeyboardButton("✅ Subscribed", callback_data="subscribed")]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                "✅ Channel joined!\n\nNow please subscribe to our YouTube channel:",
                reply_markup=reply_markup
            )
        else:
            await query.edit_message_text("⚠️ Please join the channel first: @parishram_2025_1_0")
    except Exception as e:
        await query.edit_message_text(f"❌ Error checking channel membership: {e}")


# ---------------- Step 2: Subscribed ----------------
async def subscribed_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    video_id = context.user_data.get("video_id")

    if not video_id:
        await query.edit_message_text("❌ Invalid or missing video ID. Please try again with /start?v=302")
        return

    try:
        await context.bot.forward_message(
            chat_id=user_id,
            from_chat_id=CHANNEL_FORWARD_ID,
            message_id=int(video_id)   # yahi important line hai
        )
        await query.edit_message_text("🎉 Here is your lecture 👇")
    except Exception as e:
        await query.edit_message_text(f"⚠️ Error forwarding video: {e}")


# ---------------- Run Bot ----------------
if __name__ == "__main__":
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(joined_callback, pattern="joined"))
    app.add_handler(CallbackQueryHandler(subscribed_callback, pattern="subscribed"))

    print("🤖 Bot is running...")
    app.run_polling()
