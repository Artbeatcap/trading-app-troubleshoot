#!/usr/bin/env python3
"""
Comprehensive test for Google OAuth flow and potential issues
"""

import os
import sys
from datetime import datetime

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, UserSettings

def test_google_oauth_flow():
    """Test Google OAuth flow and potential issues"""
    
    with app.app_context():
        print("Testing Google OAuth flow and potential issues...")
        print("=" * 60)
        
        try:
            # Check existing users
            print("Checking existing users...")
            users = User.query.all()
            print(f"Total users in database: {len(users)}")
            
            for user in users[:5]:  # Show first 5 users
                print(f"  User: {user.username} (ID: {user.id}, Email: {user.email})")
            
            # Test creating user with existing email (this might be the issue)
            print("\nTesting duplicate email scenario...")
            existing_email = "test@example.com"
            
            # Check if email already exists
            existing_user = User.query.filter_by(email=existing_email).first()
            if existing_user:
                print(f"❌ Email {existing_email} already exists (User ID: {existing_user.id})")
                print("This could be causing the 'Error creating user account' message")
            else:
                print(f"✅ Email {existing_email} does not exist")
            
            # Test creating a completely new user
            print("\nTesting new user creation...")
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            new_email = f"new_user_{timestamp}@example.com"
            new_username = f"new_user_{timestamp}"
            
            # Check if this email/username already exists
            existing_user = User.query.filter_by(email=new_email).first()
            if existing_user:
                print(f"❌ Email {new_email} already exists")
            else:
                print(f"✅ Email {new_email} is available")
            
            existing_user = User.query.filter_by(username=new_username).first()
            if existing_user:
                print(f"❌ Username {new_username} already exists")
            else:
                print(f"✅ Username {new_username} is available")
            
            # Create the new user
            try:
                new_user = User(
                    username=new_username,
                    email=new_email,
                    email_verified=True,
                    created_at=datetime.utcnow()
                )
                
                db.session.add(new_user)
                db.session.flush()
                
                print(f"✅ New user created: ID {new_user.id}")
                
                # Create user settings
                user_settings = UserSettings(
                    user_id=new_user.id,
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
                print("✅ Complete Google OAuth flow simulation successful")
                
                # Clean up
                db.session.delete(user_settings)
                db.session.delete(new_user)
                db.session.commit()
                print("✅ Test data cleaned up")
                
            except Exception as e:
                print(f"❌ Error creating new user: {e}")
                db.session.rollback()
                import traceback
                traceback.print_exc()
            
            # Check for any potential issues
            print("\nChecking for potential issues...")
            
            # Check if there are any users without settings
            users_without_settings = []
            for user in User.query.all():
                settings = UserSettings.query.filter_by(user_id=user.id).first()
                if not settings:
                    users_without_settings.append(user)
            
            if users_without_settings:
                print(f"❌ Found {len(users_without_settings)} users without settings:")
                for user in users_without_settings[:3]:
                    print(f"  User: {user.username} (ID: {user.id})")
            else:
                print("✅ All users have settings records")
            
            print("\n✅ Google OAuth flow test completed")
            
        except Exception as e:
            print(f"❌ Error testing Google OAuth flow: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    test_google_oauth_flow()



