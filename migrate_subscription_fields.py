#!/usr/bin/env python3
"""
Migration script to add subscription fields to User model.
Run this script to update your database schema.
"""

import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User

def migrate_subscription_fields():
    """Add subscription fields to User table"""
    with app.app_context():
        try:
            # Check if columns already exist
            inspector = db.inspect(db.engine)
            existing_columns = [col['name'] for col in inspector.get_columns('user')]
            
            columns_to_add = [
                'subscription_status',
                'plan_type', 
                'stripe_customer_id',
                'stripe_subscription_id'
            ]
            
            missing_columns = [col for col in columns_to_add if col not in existing_columns]
            
            if not missing_columns:
                print("✅ All subscription columns already exist")
                return
            
            print(f"Adding missing columns: {missing_columns}")
            
            # Add columns one by one
            for column in missing_columns:
                try:
                    if column == 'subscription_status':
                        with db.engine.connect() as conn:
                            conn.execute(db.text("ALTER TABLE \"user\" ADD COLUMN subscription_status VARCHAR(20) DEFAULT 'free'"))
                            conn.commit()
                    elif column == 'plan_type':
                        with db.engine.connect() as conn:
                            conn.execute(db.text("ALTER TABLE \"user\" ADD COLUMN plan_type VARCHAR(20) DEFAULT 'none'"))
                            conn.commit()
                    elif column == 'stripe_customer_id':
                        with db.engine.connect() as conn:
                            conn.execute(db.text("ALTER TABLE \"user\" ADD COLUMN stripe_customer_id VARCHAR(100) UNIQUE"))
                            conn.commit()
                    elif column == 'stripe_subscription_id':
                        with db.engine.connect() as conn:
                            conn.execute(db.text("ALTER TABLE \"user\" ADD COLUMN stripe_subscription_id VARCHAR(100) UNIQUE"))
                            conn.commit()
                    
                    print(f"✅ Added column: {column}")
                except Exception as e:
                    print(f"⚠️  Error adding column {column}: {e}")
            
            # Update existing users to have 'free' subscription status
            try:
                with db.engine.connect() as conn:
                    conn.execute(db.text("UPDATE \"user\" SET subscription_status = 'free' WHERE subscription_status IS NULL"))
                    conn.execute(db.text("UPDATE \"user\" SET plan_type = 'none' WHERE plan_type IS NULL"))
                    conn.commit()
                print("✅ Updated existing users with default subscription values")
            except Exception as e:
                print(f"⚠️  Error updating existing users: {e}")
            
            print("✅ Migration completed successfully!")
            
        except Exception as e:
            print(f"❌ Migration failed: {e}")
            raise

if __name__ == "__main__":
    print("Starting subscription fields migration...")
    migrate_subscription_fields()
    print("Migration script completed.")
