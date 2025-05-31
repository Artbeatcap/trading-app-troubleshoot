#!/usr/bin/env python3
"""
Database migration script to add chart image columns
"""

from app import app
from models import db
import sqlite3

def migrate_database():
    """Add new columns to existing database"""
    with app.app_context():
        try:
            # Add image columns to Trade table
            with db.engine.connect() as conn:
                conn.execute(db.text('ALTER TABLE trade ADD COLUMN entry_chart_image VARCHAR(200)'))
                conn.commit()
            print("✅ Added entry_chart_image column to trade table")
        except Exception as e:
            print(f"⚠️  entry_chart_image column might already exist: {e}")
        
        try:
            with db.engine.connect() as conn:
                conn.execute(db.text('ALTER TABLE trade ADD COLUMN exit_chart_image VARCHAR(200)'))
                conn.commit()
            print("✅ Added exit_chart_image column to trade table")
        except Exception as e:
            print(f"⚠️  exit_chart_image column might already exist: {e}")
        
        try:
            # Add chart_analysis column to TradeAnalysis table
            with db.engine.connect() as conn:
                conn.execute(db.text('ALTER TABLE trade_analysis ADD COLUMN chart_analysis TEXT'))
                conn.commit()
            print("✅ Added chart_analysis column to trade_analysis table")
        except Exception as e:
            print(f"⚠️  chart_analysis column might already exist: {e}")
        
        print("\n🎉 Database migration completed!")

if __name__ == "__main__":
    print("🚀 Starting database migration...")
    migrate_database() 