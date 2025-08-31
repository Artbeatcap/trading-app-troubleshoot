#!/usr/bin/env python3
"""
Migration script to add trial-related fields to User table
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
            # Check if columns already exist
            inspector = db.inspect(db.engine)
            existing_columns = [col['name'] for col in inspector.get_columns('user')]
            
            if 'trial_end' not in existing_columns:
                print("Adding trial_end column...")
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE "user" ADD COLUMN trial_end TIMESTAMP'))
                    conn.commit()
                print("✓ Added trial_end column")
            else:
                print("✓ trial_end column already exists")
                
            if 'had_trial' not in existing_columns:
                print("Adding had_trial column...")
                with db.engine.connect() as conn:
                    conn.execute(db.text('ALTER TABLE "user" ADD COLUMN had_trial BOOLEAN DEFAULT FALSE'))
                    conn.commit()
                print("✓ Added had_trial column")
            else:
                print("✓ had_trial column already exists")
                
            print("\nMigration completed successfully!")
            
        except Exception as e:
            print(f"Migration failed: {e}")
            db.session.rollback()
            raise

if __name__ == "__main__":
    migrate_trial_fields()
