import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text
from app.database import engine

def migrate():
    print("--- Applying Schema Migration ---")
    with engine.connect() as conn:
        try:
            # Upgrade telegram_id to BigInteger
            print("Altering 'users' table: telegram_id -> BigInteger...")
            conn.execute(text("ALTER TABLE users ALTER COLUMN telegram_id TYPE BIGINT"))
            conn.commit()
            print("Migration successful!")
        except Exception as e:
            print(f"Migration error (this is okay if table hasn't been created yet): {e}")

if __name__ == "__main__":
    migrate()
