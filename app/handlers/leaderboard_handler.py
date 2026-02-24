import logging
import os
from telegram import Update
from telegram.ext import ContextTypes
from ..services.leaderboard_service import LeaderboardService

logger = logging.getLogger(__name__)

async def leaderboard_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles the /leaderboard command."""
    top_users = LeaderboardService.get_top_users()
    formatted_text = LeaderboardService.format_leaderboard(top_users)
    await update.message.reply_text(formatted_text, parse_mode="Markdown")

async def post_weekly_leaderboard(context: ContextTypes.DEFAULT_TYPE):
    """Job task to post the leaderboard to a channel."""
    channel_id = os.getenv("LEADERBOARD_CHANNEL_ID")
    
    if not channel_id:
        logger.warning("LEADERBOARD_CHANNEL_ID not set. Skipping auto-post.")
        return

    logger.info("Executing scheduled leaderboard auto-post...")
    top_users = LeaderboardService.get_top_users()
    formatted_text = LeaderboardService.format_leaderboard(top_users)
    
    try:
        await context.bot.send_message(
            chat_id=channel_id,
            text=f"📊 *Weekly Update*\n\n{formatted_text}",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Failed to post weekly leaderboard: {e}")
