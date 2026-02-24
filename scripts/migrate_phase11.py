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
    
    print("Running Phase 11 Migration...")
    
    with engine.connect() as conn:
        try:
            print("Making 'telegram_id' nullable in users table...")
            # In PostgreSQL, columns are nullable by default, but if it was NOT NULL, we need to alter it
            conn.execute(text("ALTER TABLE users ALTER COLUMN telegram_id DROP NOT NULL;"))
            
            conn.commit()
            print("Migration successful! [Phase 11]")
        except Exception as e:
            print(f"Migration error: {e}")
            conn.rollback()

if __name__ == "__main__":
    migrate()
