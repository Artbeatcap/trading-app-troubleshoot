#!/usr/bin/env python3
"""
Script to check and fix database permissions
"""

import os
import sys
from datetime import datetime

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from sqlalchemy import text

def check_and_fix_permissions():
    """Check and fix database permissions"""
    
    with app.app_context():
        print("Checking database permissions...")
        print("=" * 50)
        
        try:
            with db.engine.connect() as conn:
                # Check current permissions on user_settings_id_seq
                result = conn.execute(text("""
                    SELECT grantee, privilege_type 
                    FROM information_schema.usage_privileges 
                    WHERE object_name = 'user_settings_id_seq';
                """))
                
                print("Current permissions on user_settings_id_seq:")
                permissions = []
                for row in result:
                    permissions.append(f"{row[0]}: {row[1]}")
                    print(f"  {row[0]}: {row[1]}")
                
                if not permissions:
                    print("  No explicit permissions found")
                
                # Check if tradingapp user has permissions
                tradingapp_has_permissions = any('tradingapp' in perm for perm in permissions)
                
                if not tradingapp_has_permissions:
                    print("\n❌ tradingapp user does not have permissions on user_settings_id_seq")
                    print("Attempting to fix permissions...")
                    
                    # Try to grant permissions
                    try:
                        conn.execute(text("GRANT USAGE, SELECT ON SEQUENCE user_settings_id_seq TO tradingapp"))
                        conn.execute(text("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO tradingapp"))
                        print("✅ Permissions granted successfully")
                        
                        # Check permissions again
                        result = conn.execute(text("""
                            SELECT grantee, privilege_type 
                            FROM information_schema.usage_privileges 
                            WHERE object_name = 'user_settings_id_seq';
                        """))
                        
                        print("\nUpdated permissions:")
                        for row in result:
                            print(f"  {row[0]}: {row[1]}")
                            
                    except Exception as e:
                        print(f"❌ Failed to grant permissions: {e}")
                        print("You may need to run this as a superuser")
                        
                else:
                    print("\n✅ tradingapp user has permissions on user_settings_id_seq")
                    
                # Test if we can actually use the sequence
                try:
                    result = conn.execute(text("SELECT nextval('user_settings_id_seq')"))
                    next_val = result.fetchone()[0]
                    print(f"✅ Successfully used sequence, next value: {next_val}")
                except Exception as e:
                    print(f"❌ Failed to use sequence: {e}")
                    
        except Exception as e:
            print(f"❌ Error checking permissions: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    check_and_fix_permissions()




