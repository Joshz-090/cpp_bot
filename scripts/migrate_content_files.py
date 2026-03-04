#!/usr/bin/env python3
"""
Migration script to add ContentFile table for multiple file support
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import engine, Base
from app.models import ContentFile
from sqlalchemy import text

def migrate_content_files():
    """Create the ContentFile table"""
    print("Creating ContentFile table...")
    
    try:
        # Create the table
        ContentFile.__table__.create(engine, checkfirst=True)
        print("✅ ContentFile table created successfully!")
        
        # Verify table exists (PostgreSQL version)
        with engine.connect() as conn:
            result = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_name='content_files'"))
            if result.fetchone():
                print("✅ Verification: ContentFile table exists in database")
            else:
                print("❌ Verification failed: ContentFile table not found")
                
    except Exception as e:
        print(f"❌ Error creating ContentFile table: {e}")
        return False
    
    return True

if __name__ == "__main__":
    print("🚀 Starting ContentFile migration...")
    success = migrate_content_files()
    
    if success:
        print("🎉 Migration completed successfully!")
        print("\nNew features available:")
        print("- Multiple PDF uploads per week")
        print("- Multiple video links per week") 
        print("- File management in admin panel")
    else:
        print("❌ Migration failed!")
        sys.exit(1)
