#!/usr/bin/env python3
"""
Script to check database sequences and permissions
"""

import os
import sys
from datetime import datetime

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from sqlalchemy import text

def check_sequences():
    """Check database sequences and permissions"""
    
    with app.app_context():
        print("Checking database sequences...")
        print("=" * 50)
        
        try:
            with db.engine.connect() as conn:
                # Check if user_settings_id_seq exists
                result = conn.execute(text("""
                    SELECT sequence_name 
                    FROM information_schema.sequences 
                    WHERE sequence_name = 'user_settings_id_seq';
                """))
                
                if result.fetchone():
                    print("✅ user_settings_id_seq sequence exists")
                    
                    # Check sequence permissions
                    result = conn.execute(text("""
                        SELECT grantee, privilege_type 
                        FROM information_schema.usage_privileges 
                        WHERE object_name = 'user_settings_id_seq';
                    """))
                    
                    print("\nSequence permissions:")
                    permissions = []
                    for row in result:
                        permissions.append(f"{row[0]}: {row[1]}")
                        print(f"  {row[0]}: {row[1]}")
                    
                    if not permissions:
                        print("  No explicit permissions found")
                        
                else:
                    print("❌ user_settings_id_seq sequence does not exist")
                    
                # Check if users table has dark_mode column
                result = conn.execute(text("""
                    SELECT column_name, data_type
                    FROM information_schema.columns 
                    WHERE table_name = 'user' AND column_name = 'dark_mode';
                """))
                
                if result.fetchone():
                    print("\n✅ dark_mode column exists in user table")
                else:
                    print("\n❌ dark_mode column does not exist in user table")
                    
                # Check user table structure
                result = conn.execute(text("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns 
                    WHERE table_name = 'user'
                    ORDER BY ordinal_position;
                """))
                
                print("\nuser table structure:")
                for row in result:
                    print(f"  {row[0]}: {row[1]} ({'NULL' if row[2] == 'YES' else 'NOT NULL'})")
                    
        except Exception as e:
            print(f"❌ Error checking sequences: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    check_sequences()




