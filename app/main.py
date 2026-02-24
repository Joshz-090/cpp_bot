import logging
import os
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes, CallbackQueryHandler
from .config import Config
from .database import init_db
from .handlers.admin_handler import admin_menu, admin_conv_handler
from datetime import time
from .handlers import student_handler
from .handlers.leaderboard_handler import leaderboard_command, post_weekly_leaderboard

# --- Logging Setup ---
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

def main():
    """Run the bot."""
    # Initialize the database
    logger.info("Initializing database...")
    init_db()
    
    # Build the application
    application = ApplicationBuilder().token(Config.BOT_TOKEN).build()

    # Add handlers
    application.add_handler(student_handler.student_conv_handler) # Replaces simple /start
    application.add_handler(CommandHandler("help", student_handler.help_command))
    application.add_handler(CommandHandler("stats", student_handler.stats_command))
    application.add_handler(CommandHandler("forgot", student_handler.forgot_password))
    application.add_handler(CommandHandler("logout", student_handler.logout_command))
    application.add_handler(CommandHandler("leaderboard", leaderboard_command))
    
    application.add_handler(student_handler.quiz_list_handler)
    application.add_handler(admin_conv_handler)

    # --- Job Queue - Weekly Leaderboard ---
    if application.job_queue:
        # Schedule for Sunday at 21:00 (9 PM)
        # Note: '6' represents Sunday (0 is Monday) in some libraries, 
        # but PTB uses 0-6 where 0 is Monday or specific weekdays.
        # We'll use day=6 for Sunday.
        application.job_queue.run_daily(
            post_weekly_leaderboard,
            time=time(hour=21, minute=0),
            days=(6,)
        )
        logger.info("Weekly leaderboard job scheduled for Sundays at 21:00")

    # --- Polling vs Webhook ---
    if Config.ENV == "production":
        # PRODUCTION: Webhook setup
        # Note: In production, you typically need a URL and port (e.g., from Render)
        PORT = int(os.environ.get("PORT", "8443"))
        WEBHOOK_URL = os.environ.get("WEBHOOK_URL") 
        
        if not WEBHOOK_URL:
            logger.warning("WEBHOOK_URL not set, falling back to polling.")
            application.run_polling()
        else:
            logger.info(f"Starting in WEBHOOK mode on port {PORT}")
            application.run_webhook(
                listen="0.0.0.0",
                port=PORT,
                url_path=Config.BOT_TOKEN,
                webhook_url=f"{WEBHOOK_URL}/{Config.BOT_TOKEN}"
            )
    else:
        # DEVELOPMENT: Polling
        logger.info("Starting in POLLING mode")
        application.run_polling()

if __name__ == '__main__':
    main()
