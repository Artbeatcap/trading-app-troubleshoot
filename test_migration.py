#!/usr/bin/env python3
"""
Test script to verify the trial fields migration
"""
from app import app, db
from models import User

def test_migration():
    with app.app_context():
        try:
            # Check if we can query the User table
            user_count = User.query.count()
            print(f"✓ Database connection working. User count: {user_count}")
            
            # Check if the new columns exist
            columns = [c.name for c in User.__table__.columns]
            print(f"✓ User table columns: {columns}")
            
            # Check for our new columns
            if 'trial_end' in columns:
                print("✓ trial_end column exists")
            else:
                print("✗ trial_end column missing")
                
            if 'had_trial' in columns:
                print("✓ had_trial column exists")
            else:
                print("✗ had_trial column missing")
                
            print("\nMigration test completed!")
            
        except Exception as e:
            print(f"✗ Error: {e}")

if __name__ == "__main__":
    test_migration()
