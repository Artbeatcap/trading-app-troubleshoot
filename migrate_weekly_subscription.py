#!/usr/bin/env python3
"""
Database migration to add weekly subscription fields to users table.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

def run_migration():
    """Add weekly subscription fields to users table."""
    
    # Import app to get database configuration
    from app import app, db
    
    with app.app_context():
        try:
            # Add weekly subscription fields
            print("Adding weekly subscription fields to users table...")
            
            # Add is_subscribed_weekly field
            db.session.execute(text("""
                ALTER TABLE "user" 
                ADD COLUMN IF NOT EXISTS is_subscribed_weekly BOOLEAN DEFAULT TRUE
            """))
            
            # Add is_subscribed_daily field (if not exists)
            db.session.execute(text("""
                ALTER TABLE "user" 
                ADD COLUMN IF NOT EXISTS is_subscribed_daily BOOLEAN DEFAULT FALSE
            """))
            
            # Create email_deliveries table if it doesn't exist
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS email_deliveries (
                    id SERIAL PRIMARY KEY,
                    user_id INTEGER NOT NULL,
                    kind VARCHAR(16) NOT NULL,
                    subject TEXT NOT NULL,
                    sent_at TIMESTAMP NOT NULL DEFAULT NOW(),
                    provider_id TEXT
                )
            """))
            
            # Commit the changes
            db.session.commit()
            
            print("✅ Migration completed successfully!")
            print("Added fields:")
            print("  - users.is_subscribed_weekly (default: TRUE)")
            print("  - users.is_subscribed_daily (default: FALSE)")
            print("  - email_deliveries table")
            
        except Exception as e:
            print(f"❌ Database error: {e}")
            db.session.rollback()
            sys.exit(1)

if __name__ == "__main__":
    run_migration()
