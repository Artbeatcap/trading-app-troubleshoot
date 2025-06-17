#!/usr/bin/env python3
"""
Database migration script to add journal_date column to trading_journal table
"""

from app import app
from models import db
from datetime import datetime

def migrate_database():
    """Add journal_date column to trading_journal table"""
    with app.app_context():
        try:
            # Add journal_date column to trading_journal table
            with db.engine.connect() as conn:
                conn.execute(db.text('ALTER TABLE trading_journal ADD COLUMN journal_date DATE'))
                conn.commit()
            print("✅ Added journal_date column to trading_journal table")
            
            # Set default value for existing records
            with db.engine.connect() as conn:
                conn.execute(db.text('UPDATE trading_journal SET journal_date = created_at WHERE journal_date IS NULL'))
                conn.commit()
            print("✅ Updated existing records with default journal_date")
            
        except Exception as e:
            print(f"⚠️  Error during migration: {e}")
        
        print("\n🎉 Journal date migration completed!")

if __name__ == "__main__":
    print("🚀 Starting journal date migration...")
    migrate_database() 