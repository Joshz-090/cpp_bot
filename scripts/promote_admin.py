import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app.services.user_service import UserService

def promote(telegram_id):
    print(f"--- Promoting User {telegram_id} to Admin ---")
    success = UserService.set_admin(telegram_id)
    if success:
        print("✅ Success! You are now an admin.")
    else:
        print("❌ Failed. Ensure you have messaged the bot at least once so your account exists in the database.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/promote_admin.py <YOUR_TELEGRAM_ID>")
    else:
        promote(int(sys.argv[1]))
