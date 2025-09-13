#!/usr/bin/env python3
"""
Script to check database tables
"""

import os
import sys
from datetime import datetime

# Add the current directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from sqlalchemy import text

def check_database_tables():
    """Check what tables exist in the database"""
    
    with app.app_context():
        print("Checking database tables...")
        print("=" * 50)
        
        try:
            # Get all tables
            with db.engine.connect() as conn:
                result = conn.execute(text("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    ORDER BY table_name;
                """))
                
                print("Tables in database:")
                tables = []
                for row in result:
                    tables.append(row[0])
                    print(f"  {row[0]}")
                
                print(f"\nTotal tables: {len(tables)}")
                
                # Check if user_settings table exists
                if 'user_settings' in tables:
                    print("\n✅ user_settings table exists")
                    
                    # Check table structure
                    result = conn.execute(text("""
                        SELECT column_name, data_type, is_nullable
                        FROM information_schema.columns 
                        WHERE table_name = 'user_settings'
                        ORDER BY ordinal_position;
                    """))
                    
                    print("\nuser_settings table structure:")
                    for row in result:
                        print(f"  {row[0]}: {row[1]} ({'NULL' if row[2] == 'YES' else 'NOT NULL'})")
                        
                else:
                    print("\n❌ user_settings table does not exist")
                    
                # Check if users table exists and has dark_mode column
                if 'users' in tables:
                    print("\n✅ users table exists")
                    
                    # Check if dark_mode column exists
                    result = conn.execute(text("""
                        SELECT column_name, data_type
                        FROM information_schema.columns 
                        WHERE table_name = 'users' AND column_name = 'dark_mode';
                    """))
                    
                    if result.fetchone():
                        print("✅ dark_mode column exists in users table")
                    else:
                        print("❌ dark_mode column does not exist in users table")
                        
        except Exception as e:
            print(f"❌ Error checking database: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    check_database_tables()

