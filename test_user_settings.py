#!/usr/bin/env python3
"""
Test script to check user settings database operations
"""

import os
import sys
from datetime import datetime

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, UserSettings

def test_user_settings():
    """Test user settings database operations"""
    
    with app.app_context():
        print("Testing user settings database operations...")
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
            
            # Check if user has settings record
            user_settings = UserSettings.query.filter_by(user_id=user.id).first()
            
            if user_settings:
                print(f"✅ User settings found: ID {user_settings.id}")
                print(f"  Auto analyze trades: {user_settings.auto_analyze_trades}")
                print(f"  Auto create journal: {user_settings.auto_create_journal}")
                print(f"  Analysis detail level: {user_settings.analysis_detail_level}")
                print(f"  Daily journal reminder: {user_settings.daily_journal_reminder}")
                print(f"  Weekly summary: {user_settings.weekly_summary}")
                print(f"  Default chart timeframe: {user_settings.default_chart_timeframe}")
                print(f"  Trades per page: {user_settings.trades_per_page}")
                print(f"  Default risk percent: {user_settings.default_risk_percent}")
                
                # Test updating the settings
                print("\nTesting settings update...")
                try:
                    user_settings.auto_analyze_trades = not user_settings.auto_analyze_trades
                    user_settings.updated_at = datetime.utcnow()
                    db.session.commit()
                    print("✅ Settings updated successfully")
                except Exception as e:
                    print(f"❌ Failed to update settings: {e}")
                    db.session.rollback()
                    
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
                        default_risk_percent=2.0,
                        created_at=datetime.utcnow(),
                        updated_at=datetime.utcnow()
                    )
                    
                    db.session.add(new_settings)
                    db.session.commit()
                    print("✅ User settings record created successfully")
                    
                except Exception as e:
                    print(f"❌ Failed to create user settings: {e}")
                    db.session.rollback()
                    import traceback
                    traceback.print_exc()
            
            # Test dark mode toggle
            print("\nTesting dark mode toggle...")
            try:
                user.dark_mode = not user.dark_mode
                db.session.commit()
                print(f"✅ Dark mode toggled to: {user.dark_mode}")
            except Exception as e:
                print(f"❌ Failed to toggle dark mode: {e}")
                db.session.rollback()
            
            print("\n✅ User settings test completed successfully")
            
        except Exception as e:
            print(f"❌ Error testing user settings: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_user_settings()



