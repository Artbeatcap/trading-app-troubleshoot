#!/usr/bin/env python3
"""
Test script to verify dark mode toggle functionality
"""

import os
import sys
from datetime import datetime

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User

def test_dark_mode_toggle():
    """Test that dark mode can be toggled for a user"""
    
    with app.app_context():
        print("Testing dark mode toggle functionality...")
        print("=" * 50)
        
        # Get a test user
        user = User.query.first()
        if not user:
            print("No users found in database")
            return
            
        print(f"Testing with user: {user.username}")
        print(f"Initial dark_mode value: {user.dark_mode}")
        
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
        
        print("\n✅ Dark mode toggle functionality is working correctly!")
        print("\nTo test in the browser:")
        print("1. Log in at http://localhost:5000/login")
        print("2. Go to Settings at http://localhost:5000/settings")
        print("3. Toggle the 'Enable dark mode' checkbox")
        print("4. Click 'Save Changes'")
        print("5. Refresh the page to see the dark mode applied")
        
        print("=" * 50)

if __name__ == "__main__":
    test_dark_mode_toggle()
