import os
import sys
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

# Add the project root to sys.path to import from app
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def migrate():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("Error: DATABASE_URL not found in .env")
        return

    # Neon.tech workaround for sqlalchemy
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    engine = create_engine(db_url)
    
    print("Running Phase 9 Migration...")
    
    with engine.connect() as conn:
        # Add availability columns to quizzes
        try:
            print("Adding 'available_from' to quizzes...")
            conn.execute(text("ALTER TABLE quizzes ADD COLUMN IF NOT EXISTS available_from TIMESTAMP;"))
            
            print("Adding 'available_until' to quizzes...")
            conn.execute(text("ALTER TABLE quizzes ADD COLUMN IF NOT EXISTS available_until TIMESTAMP;"))
            
            conn.commit()
            print("Migration successful! [Phase 9]")
        except Exception as e:
            print(f"Migration error: {e}")
            conn.rollback()

if __name__ == "__main__":
    migrate()
