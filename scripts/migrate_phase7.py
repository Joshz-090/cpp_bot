import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from sqlalchemy import text
from app.database import engine

def migrate():
    print("--- Applying Phase 7 Schema Migration ---")
    with engine.connect() as conn:
        try:
            print("Enforcing UNIQUE constraint on 'nickname'...")
            # We use a subquery to find duplicates first if any exist
            # But since it's a new feature, we'll try to apply directly
            conn.execute(text("ALTER TABLE users ADD CONSTRAINT unique_nickname UNIQUE (nickname)"))
            conn.commit()
            print("Migration successful!")
        except Exception as e:
            print(f"Migration error: {e}")

if __name__ == "__main__":
    migrate()
