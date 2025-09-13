#!/usr/bin/env python3
"""
Script to fix users without settings records
"""

import os
import sys
from datetime import datetime

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import User, UserSettings

def fix_users_without_settings():
    """Fix users without settings records"""
    
    with app.app_context():
        print("Fixing users without settings records...")
        print("=" * 50)
        
        try:
            # Find users without settings
            users_without_settings = []
            for user in User.query.all():
                settings = UserSettings.query.filter_by(user_id=user.id).first()
                if not settings:
                    users_without_settings.append(user)
            
            print(f"Found {len(users_without_settings)} users without settings")
            
            if users_without_settings:
                print("Creating settings for users without them...")
                
                for user in users_without_settings:
                    print(f"Creating settings for user: {user.username} (ID: {user.id})")
                    
                    try:
                        user_settings = UserSettings(
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
                        
                        db.session.add(user_settings)
                        print(f"  ✅ Settings created for user {user.username}")
                        
                    except Exception as e:
                        print(f"  ❌ Error creating settings for user {user.username}: {e}")
                
                # Commit all changes
                try:
                    db.session.commit()
                    print(f"✅ Successfully created settings for {len(users_without_settings)} users")
                except Exception as e:
                    print(f"❌ Error committing changes: {e}")
                    db.session.rollback()
            else:
                print("✅ All users already have settings records")
            
            # Verify the fix
            print("\nVerifying fix...")
            users_without_settings_after = []
            for user in User.query.all():
                settings = UserSettings.query.filter_by(user_id=user.id).first()
                if not settings:
                    users_without_settings_after.append(user)
            
            if users_without_settings_after:
                print(f"❌ Still found {len(users_without_settings_after)} users without settings")
            else:
                print("✅ All users now have settings records")
            
        except Exception as e:
            print(f"❌ Error fixing users without settings: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    fix_users_without_settings()



