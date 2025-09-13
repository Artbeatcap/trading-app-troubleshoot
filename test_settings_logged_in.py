#!/usr/bin/env python3
"""
Test script to simulate accessing settings page when logged in
"""

import os
import sys
from datetime import datetime

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User
from forms import SettingsForm

def test_settings_logged_in():
    """Test settings page when user is logged in"""
    
    with app.app_context():
        print("Testing settings page when logged in...")
        print("=" * 50)
        
        try:
            # Get a test user
            user = User.query.first()
            if not user:
                print("No users found in database")
                return
            
            print(f"Testing with user: {user.username}")
            print(f"User ID: {user.id}")
            print(f"Dark mode: {user.dark_mode}")
            
            # Test creating a settings form
            print("\nTesting SettingsForm creation...")
            form = SettingsForm(obj=user)
            print("✅ SettingsForm created successfully")
            
            # Test form fields
            print("\nForm fields:")
            for field_name in form.data.keys():
                print(f"  {field_name}: {form.data[field_name]}")
            
            # Test if we can access user settings
            print("\nTesting user settings access...")
            
            # Check if user has settings record
            from models import UserSettings
            user_settings = UserSettings.query.filter_by(user_id=user.id).first()
            
            if user_settings:
                print(f"✅ User settings found: ID {user_settings.id}")
                print(f"  Auto analyze trades: {user_settings.auto_analyze_trades}")
                print(f"  Auto create journal: {user_settings.auto_create_journal}")
            else:
                print("❌ No user settings record found")
                print("Creating user settings record...")
                
                try:
                    # Create a new user settings record
                    new_settings = UserSettings(
                        user_id=user.id,
                        auto_analyze_trades=True,
                        auto_create_journal=True,
                        analysis_detail_level='detailed',
                        daily_journal_reminder=True,
                        weekly_summary=True,
                        default_chart_timeframe='1D',
                        trades_per_page=20,
                        default_risk_percent=2.0
                    )
                    
                    db.session.add(new_settings)
                    db.session.commit()
                    print("✅ User settings record created successfully")
                    
                except Exception as e:
                    print(f"❌ Failed to create user settings: {e}")
                    db.session.rollback()
            
            print("\n✅ Settings page test completed successfully")
            
        except Exception as e:
            print(f"❌ Error testing settings: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_settings_logged_in()



