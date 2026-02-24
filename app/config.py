import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    DATABASE_URL = os.getenv("DATABASE_URL")
    ENV = os.getenv("ENV", "development")
    LEADERBOARD_CHANNEL_ID = os.getenv("LEADERBOARD_CHANNEL_ID")
    STUDENT_ACCESS_PASSWORD = os.getenv("STUDENT_ACCESS_PASSWORD", "cpp123")
    
    @classmethod
    def validate(cls):
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN is missing! Please set it in the .env file.")
        if not cls.DATABASE_URL:
            raise ValueError("DATABASE_URL is missing! Please set it in the .env file.")

# Validate configuration on import
Config.validate()
