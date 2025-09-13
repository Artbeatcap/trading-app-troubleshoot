#!/usr/bin/env python3
"""
Test script to verify Google OAuth account creation
"""

import os
import sys
from datetime import datetime

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, UserSettings

def test_google_oauth_creation():
    """Test Google OAuth account creation process"""
    
    with app.app_context():
        print("Testing Google OAuth account creation...")
        print("=" * 50)
        
        try:
            # Simulate creating a new user (like Google OAuth would do)
            print("Creating test user...")
            
            # Create a test user
            test_user = User(
                username=f"test_google_user_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                email=f"test_google_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com",
                email_verified=True,
                created_at=datetime.utcnow()
            )
            
            db.session.add(test_user)
            db.session.flush()  # This will generate the user ID
            
            print(f"✅ Test user created: ID {test_user.id}")
            
            # Now create user settings (this is where the error was occurring)
            print("Creating user settings...")
            
            user_settings = UserSettings(
                user_id=test_user.id,
                auto_analyze_trades=True,
                auto_create_journal=True,
                analysis_detail_level='detailed',
                daily_journal_reminder=True,
                weekly_summary=True,
                default_chart_timeframe='1D',
                trades_per_page=20,
                default_risk_percent=2.0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow()
            )
            
            db.session.add(user_settings)
            db.session.commit()
            
            print(f"✅ User settings created: ID {user_settings.id}")
            print("✅ Google OAuth account creation test completed successfully")
            
            # Clean up - remove the test user
            print("Cleaning up test data...")
            db.session.delete(user_settings)
            db.session.delete(test_user)
            db.session.commit()
            print("✅ Test data cleaned up")
            
        except Exception as e:
            print(f"❌ Error testing Google OAuth creation: {e}")
            db.session.rollback()
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_google_oauth_creation()



