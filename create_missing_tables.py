#!/usr/bin/env python3
"""
Create missing database tables
"""

import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def create_missing_tables():
    """Create missing database tables"""
    try:
        print("🔧 Creating Missing Database Tables...")
        print("=" * 50)
        
        # Import Flask app
        from app import app
        
        # Run within application context
        with app.app_context():
            from models import db
            from sqlalchemy import inspect
            
            # Check current tables
            inspector = inspect(db.engine)
            current_tables = inspector.get_table_names()
            print(f"Current tables: {current_tables}")
            
            # Create all tables
            print("\n📋 Creating all tables...")
            db.create_all()
            
            # Check tables after creation
            inspector = inspect(db.engine)
            new_tables = inspector.get_table_names()
            print(f"Tables after creation: {new_tables}")
            
            # Check if market_brief_subscriber was created
            if 'market_brief_subscriber' in new_tables:
                print("\n✅ market_brief_subscriber table created successfully!")
                
                # Show table structure
                columns = inspector.get_columns('market_brief_subscriber')
                print("\n📋 market_brief_subscriber table structure:")
                for column in columns:
                    print(f"  - {column['name']}: {column['type']}")
            else:
                print("\n❌ market_brief_subscriber table still missing")
        
        return True
        
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

if __name__ == "__main__":
    success = create_missing_tables()
    if success:
        print("\n🎉 Database tables created successfully!")
    else:
        print("\n❌ Failed to create database tables!")
        sys.exit(1)

