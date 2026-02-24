import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Add the project root to sys.path to import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

def migrate():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Error: DATABASE_URL not found in .env")
        return

    # Neon.tech workaround for sqlalchemy
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    engine = create_engine(db_url)
    
    print("Running Phase 13 Migration...")
    
    with engine.connect() as conn:
        try:
            print("Adding gamification columns to 'users' table...")
            
            # Use ALTER TABLE to add columns if they don't exist
            # Note: PostgreSQL 11+ supports adding columns with defaults without rewriting the table, 
            # and adding nullable columns is fast.
            
            # Using text() for execution
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS streak_count INTEGER DEFAULT 0;"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_activity_at TIMESTAMP;"))
            conn.execute(text("ALTER TABLE users ADD COLUMN IF NOT EXISTS badges TEXT;"))
            
            conn.commit()
            print("Migration successful! [Phase 13]")
        except Exception as e:
            print(f"Migration error: {e}")
            conn.rollback()

if __name__ == "__main__":
    migrate()
