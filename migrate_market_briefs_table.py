#!/usr/bin/env python3
"""
Database migration to add market_briefs table for storing historical briefs.
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError

def run_migration():
    """Add market_briefs table for storing historical briefs."""
    
    # Import app to get database configuration
    from app import app, db
    
    with app.app_context():
        try:
            # Create market_briefs table
            print("Creating market_briefs table...")
            
            db.session.execute(text("""
                CREATE TABLE IF NOT EXISTS market_brief (
                    id SERIAL PRIMARY KEY,
                    brief_type VARCHAR(16) NOT NULL,
                    date DATE NOT NULL,
                    subject VARCHAR(200) NOT NULL,
                    html_content TEXT NOT NULL,
                    text_content TEXT NOT NULL,
                    json_data TEXT,
                    created_at TIMESTAMP NOT NULL DEFAULT NOW()
                )
            """))
            
            # Create index for efficient queries
            db.session.execute(text("""
                CREATE INDEX IF NOT EXISTS idx_brief_type_date 
                ON market_brief (brief_type, date)
            """))
            
            # Commit the changes
            db.session.commit()
            
            print("✅ Market briefs table migration completed successfully!")
            print("Added:")
            print("  - market_brief table")
            print("  - Index on (brief_type, date)")
            
        except Exception as e:
            print(f"❌ Database error: {e}")
            db.session.rollback()
            sys.exit(1)

if __name__ == "__main__":
    run_migration()
