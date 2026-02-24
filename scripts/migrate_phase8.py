import sys
import os
from sqlalchemy import text

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine

def migrate():
    print("--- Starting Phase 8 Migration ---")
    
    with engine.connect() as conn:
        # Create quizzes table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS quizzes (
                id SERIAL PRIMARY KEY,
                title VARCHAR NOT NULL,
                description TEXT,
                duration_minutes INTEGER DEFAULT 15,
                week_number INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS ix_quizzes_id ON quizzes (id);
            CREATE INDEX IF NOT EXISTS ix_quizzes_week_number ON quizzes (week_number);
        """))
        print("[OK] Created 'quizzes' table.")

        # Add quiz_id to questions table
        # Check if column exists first to be idempotent
        res = conn.execute(text("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name='questions' AND column_name='quiz_id';
        """)).fetchone()
        
        if not res:
            conn.execute(text("ALTER TABLE questions ADD COLUMN quiz_id INTEGER REFERENCES quizzes(id);"))
            print("[OK] Added 'quiz_id' column to 'questions'.")
        else:
            print("[INFO] 'quiz_id' column already exists in 'questions'.")

        # Create quiz_attempts table
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS quiz_attempts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER NOT NULL REFERENCES users(id),
                quiz_id INTEGER NOT NULL REFERENCES quizzes(id),
                score INTEGER DEFAULT 0,
                started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                completed_at TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS ix_quiz_attempts_id ON quiz_attempts (id);
        """))
        print("[OK] Created 'quiz_attempts' table.")
        
        conn.commit()

    print("--- Phase 8 Migration Completed Successfully ---")

if __name__ == "__main__":
    migrate()
