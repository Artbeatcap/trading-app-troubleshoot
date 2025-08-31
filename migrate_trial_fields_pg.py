#!/usr/bin/env python3
"""
PostgreSQL migration script to add trial-related fields to User table
"""
import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User

def migrate_trial_fields():
    """Add trial_end and had_trial columns to User table"""
    with app.app_context():
        try:
            print("Starting PostgreSQL migration...")
            
            # Check if columns already exist using PostgreSQL-specific query
            result = db.session.execute(db.text("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'user' AND table_schema = 'public'
            """))
            existing_columns = [row[0] for row in result]
            print(f"Existing columns: {existing_columns}")
            
            if 'trial_end' not in existing_columns:
                print("Adding trial_end column...")
                db.session.execute(db.text('ALTER TABLE "user" ADD COLUMN trial_end TIMESTAMP'))
                print("✓ Added trial_end column")
            else:
                print("✓ trial_end column already exists")
                
            if 'had_trial' not in existing_columns:
                print("Adding had_trial column...")
                db.session.execute(db.text('ALTER TABLE "user" ADD COLUMN had_trial BOOLEAN DEFAULT FALSE'))
                print("✓ Added had_trial column")
            else:
                print("✓ had_trial column already exists")
                
            db.session.commit()
            print("\nMigration completed successfully!")
            
        except Exception as e:
            print(f"Migration failed: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    migrate_trial_fields()
