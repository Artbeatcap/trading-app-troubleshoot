#!/usr/bin/env python3
"""
Migration script to add new user settings fields
"""

import os
import sys
from datetime import datetime

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User

def migrate_user_settings():
    """Set default values for new user settings fields"""
    
    with app.app_context():
        print("Starting user settings default values migration...")
        
        # Get all users
        users = User.query.all()
        print(f"Found {len(users)} users to update")
        
        updated_count = 0
        for user in users:
            updated = False
            
            # Set default values for new fields
            if user.display_name is None:
                user.display_name = user.username
                updated = True
                
            if user.dark_mode is None:
                user.dark_mode = False
                updated = True
                
            if user.daily_brief_email is None:
                user.daily_brief_email = True
                updated = True
                
            if user.timezone is None:
                user.timezone = 'UTC'
                updated = True
                
            if user.api_key is None:
                user.api_key = None
                updated = True
                
            if updated:
                updated_count += 1
                print(f"Updated user: {user.username}")
        
        # Commit all changes
        try:
            db.session.commit()
            print(f"Migration completed successfully! Updated {updated_count} users.")
        except Exception as e:
            db.session.rollback()
            print(f"Migration failed: {e}")
            return False
            
        return True

if __name__ == "__main__":
    migrate_user_settings() 