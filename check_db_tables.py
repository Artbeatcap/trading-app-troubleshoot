#!/usr/bin/env python3
"""
Check database tables
"""

import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def check_database_tables():
    """Check what tables exist in the database"""
    try:
        print("🔍 Checking Database Tables...")
        print("=" * 40)
        
        # Import Flask app
        from app import app
        
        # Run within application context
        with app.app_context():
            from models import db
            from sqlalchemy import inspect
            
            inspector = inspect(db.engine)
            tables = inspector.get_table_names()
            
            print(f"Found {len(tables)} tables:")
            for table in sorted(tables):
                print(f"  ✅ {table}")
            
            # Check for market brief related tables
            market_brief_tables = [t for t in tables if 'market' in t.lower() or 'brief' in t.lower()]
            print(f"\n📧 Market brief related tables ({len(market_brief_tables)}):")
            for table in market_brief_tables:
                print(f"  ✅ {table}")
            
            # Check if market_brief_subscriber table exists
            if 'market_brief_subscriber' in tables:
                print("\n✅ market_brief_subscriber table exists")
            else:
                print("\n❌ market_brief_subscriber table is missing")
                print("   This table is needed for the market brief functionality")
        
        return True
        
    except Exception as e:
        print(f"❌ Error checking database tables: {e}")
        return False

if __name__ == "__main__":
    success = check_database_tables()
    if not success:
        sys.exit(1)

