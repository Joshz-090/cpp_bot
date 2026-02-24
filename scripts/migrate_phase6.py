import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text
from app.database import engine

def migrate():
    print("--- Applying Phase 6 Schema Migration ---")
    with engine.connect() as conn:
        try:
            print("Adding 'nickname' column to 'users'...")
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS nickname VARCHAR"))
            print("Adding 'password' column to 'users'...")
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS password VARCHAR"))
            conn.commit()
            print("Migration successful!")
        except Exception as e:
            print(f"Migration error: {e}")

if __name__ == "__main__":
    migrate()
