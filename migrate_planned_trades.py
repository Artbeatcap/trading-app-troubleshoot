#!/usr/bin/env python3
"""
Migration script to add planned trades support.

This script:
1. Adds is_planned column to Trade table
2. Makes entry_date, entry_price, quantity nullable for planned trades
3. Handles idempotent execution (safe to run multiple times)
"""

import os
import sys
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import OperationalError, ProgrammingError

def get_database_url():
    """Get database URL from environment or config"""
    # Try environment variables first
    db_url = os.getenv('DATABASE_URL')
    if db_url:
        return db_url
    
    # Fallback to config.py
    try:
        from config import Config
        return Config.SQLALCHEMY_DATABASE_URI
    except ImportError:
        print("Error: Could not find DATABASE_URL environment variable or config.py")
        sys.exit(1)

def run_migration():
    """Run the planned trades migration"""
    db_url = get_database_url()
    print(f"Connecting to database: {db_url.split('@')[-1] if '@' in db_url else db_url}")
    
    engine = create_engine(db_url)
    
    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()
        
        try:
            inspector = inspect(engine)
            columns = inspector.get_columns('trade')
            column_names = [col['name'] for col in columns]
            
            # 1. Add is_planned column if it doesn't exist
            if 'is_planned' not in column_names:
                print("Adding is_planned column...")
                conn.execute(text("ALTER TABLE trade ADD COLUMN is_planned BOOLEAN DEFAULT FALSE NOT NULL"))
                print("+ Added is_planned column")
            else:
                print("+ is_planned column already exists")
            
            # 2. Make entry_date nullable if it isn't already
            entry_date_col = next((col for col in columns if col['name'] == 'entry_date'), None)
            if entry_date_col and entry_date_col['nullable'] is False:
                print("Making entry_date nullable...")
                conn.execute(text("ALTER TABLE trade ALTER COLUMN entry_date DROP NOT NULL"))
                print("+ Made entry_date nullable")
            else:
                print("+ entry_date is already nullable")
            
            # 3. Make entry_price nullable if it isn't already
            entry_price_col = next((col for col in columns if col['name'] == 'entry_price'), None)
            if entry_price_col and entry_price_col['nullable'] is False:
                print("Making entry_price nullable...")
                conn.execute(text("ALTER TABLE trade ALTER COLUMN entry_price DROP NOT NULL"))
                print("+ Made entry_price nullable")
            else:
                print("+ entry_price is already nullable")
            
            # 4. Make quantity nullable if it isn't already
            quantity_col = next((col for col in columns if col['name'] == 'quantity'), None)
            if quantity_col and quantity_col['nullable'] is False:
                print("Making quantity nullable...")
                conn.execute(text("ALTER TABLE trade ALTER COLUMN quantity DROP NOT NULL"))
                print("+ Made quantity nullable")
            else:
                print("+ quantity is already nullable")
            
            # Commit transaction
            trans.commit()
            print("\n+ Migration completed successfully!")
            
        except Exception as e:
            # Rollback on error
            trans.rollback()
            print(f"\n- Migration failed: {e}")
            raise

if __name__ == "__main__":
    print("Planned Trades Migration")
    print("=" * 40)
    
    try:
        run_migration()
    except Exception as e:
        print(f"Migration failed: {e}")
        sys.exit(1)
