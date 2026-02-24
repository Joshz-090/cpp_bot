import asyncio
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from telegram import Bot
from app.config import Config

async def test_token():
    print(f"Testing token: {Config.BOT_TOKEN[:10]}...")
    bot = Bot(Config.BOT_TOKEN)
    try:
        me = await bot.get_me()
        print(f"SUCCESS! Bot is: @{me.username}")
    except Exception as e:
        print(f"FAILED: {e}")

if __name__ == "__main__":
    asyncio.run(test_token())
