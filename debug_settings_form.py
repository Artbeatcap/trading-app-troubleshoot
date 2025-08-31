#!/usr/bin/env python3
"""
Debug script to check SettingsForm functionality
"""

import os
import sys
from datetime import datetime

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User
from forms import SettingsForm

def debug_settings_form():
    """Debug the SettingsForm to see if fields are working correctly"""
    
    with app.app_context():
        print("Debugging SettingsForm...")
        print("=" * 50)
        
        # Get a user
        user = User.query.first()
        if not user:
            print("No users found in database")
            return
            
        print(f"Testing with user: {user.username}")
        print(f"User dark_mode value: {user.dark_mode}")
        
        # Use test client to simulate a request
        with app.test_client() as client:
            # Check if the form class has the right fields
            print("\nChecking SettingsForm class definition:")
            
            # Check if dark_mode field exists in the form class
            if hasattr(SettingsForm, 'dark_mode'):
                print("✓ dark_mode field exists in SettingsForm")
                dark_mode_field = getattr(SettingsForm, 'dark_mode')
                print(f"  Type: {type(dark_mode_field)}")
                print(f"  Arguments: {dark_mode_field.args}")
                print(f"  Kwargs: {dark_mode_field.kwargs}")
            else:
                print("✗ dark_mode field missing from SettingsForm")
                
            # Check other expected fields
            expected_fields = ['display_name', 'dark_mode', 'daily_brief_email', 'timezone']
            for field_name in expected_fields:
                if hasattr(SettingsForm, field_name):
                    print(f"✓ {field_name} field exists")
                else:
                    print(f"✗ {field_name} field missing")
                    
            # Now let's test the actual form instantiation with a request context
            print("\nTesting form instantiation with request context:")
            
            # Create a test request context
            with app.test_request_context('/settings'):
                try:
                    # Create form with user object
                    form = SettingsForm(obj=user)
                    print("✓ Form created successfully with user object")
                    
                    # Check if dark_mode field is properly bound
                    if hasattr(form, 'dark_mode'):
                        print(f"✓ dark_mode field is bound")
                        print(f"  Data: {form.dark_mode.data}")
                        print(f"  Label: {form.dark_mode.label}")
                    else:
                        print("✗ dark_mode field not found in bound form")
                        
                except Exception as e:
                    print(f"✗ Error creating form: {e}")
        
        print("=" * 50)

if __name__ == "__main__":
    debug_settings_form()
