async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

    # Handle both "/start v=1" and "/start?v=1"
    query = None
    if context.args:  # Case: /start v=1
        query = context.args[0]
    elif update.message.text and "?v=" in update.message.text:  # Case: /start?v=1
        query = update.message.text.split("?")[1]  # "v=1"

    if not query or not query.startswith("v="):
        await update.message.reply_text("Usage: /start v=1")
        return

    vid_id = query.split("=")[1]
    msg_id = VIDEO_MAP.get(vid_id)

    if not msg_id:
        await update.message.reply_text("❌ Video not found.")
        return

    # Check if user is in channel
    try:
        member = await context.bot.get_chat_member(CHANNEL_ID, user.id)
        if member.status in ["left", "kicked"]:
            join_link = f"https://t.me/{str(CHANNEL_ID)[4:]}"  
            await update.message.reply_text(
                f"🚨 Please join the channel first:\n👉 {join_link}"
            )
            return
    except Forbidden:
        await update.message.reply_text("⚠️ Bot is not admin in the channel. Please fix that.")
        return

    # Forward the video
    try:
        await context.bot.forward_message(
            chat_id=update.effective_chat.id,
            from_chat_id=CHANNEL_ID,
            message_id=msg_id
        )
    except Exception as e:
        logger.error(f"Error forwarding message: {e}")
        await update.message.reply_text("⚠️ Could not forward the video.")
