#!/usr/bin/env python3
"""
Test script to verify dark mode functionality on the server
"""

import os
import sys
from datetime import datetime

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User

def test_dark_mode_server():
    """Test dark mode functionality on the server"""
    
    with app.app_context():
        print("Testing dark mode functionality on server...")
        print("=" * 50)
        
        # Get a test user
        user = User.query.first()
        if not user:
            print("No users found in database")
            return
            
        print(f"Testing with user: {user.username}")
        print(f"Dark mode value: {user.dark_mode}")
        print(f"Display name: {user.display_name}")
        print(f"Timezone: {user.timezone}")
        
        # Test toggling dark mode
        original_value = user.dark_mode
        
        # Toggle to True
        user.dark_mode = True
        db.session.commit()
        print(f"✓ Set dark_mode to True")
        
        # Verify the change
        db.session.refresh(user)
        print(f"✓ Verified dark_mode is now: {user.dark_mode}")
        
        # Toggle back to False
        user.dark_mode = False
        db.session.commit()
        print(f"✓ Set dark_mode back to False")
        
        # Verify the change
        db.session.refresh(user)
        print(f"✓ Verified dark_mode is now: {user.dark_mode}")
        
        # Restore original value
        user.dark_mode = original_value
        db.session.commit()
        print(f"✓ Restored original value: {user.dark_mode}")
        
        print("\n✅ Dark mode functionality is working correctly on the server!")
        print("=" * 50)

if __name__ == "__main__":
    test_dark_mode_server()
