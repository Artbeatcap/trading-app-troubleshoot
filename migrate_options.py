#!/usr/bin/env python3
"""
Database migration script to add options trading fields
"""

from app import app
from models import db
import sqlite3

def migrate_database():
    """Add options-related columns to existing database"""
    with app.app_context():
        # Options-specific fields for Trade table
        options_fields = [
            ('strike_price', 'FLOAT'),
            ('expiration_date', 'DATE'),
            ('option_type', 'VARCHAR(10)'),
            ('premium_paid', 'FLOAT'),
            ('implied_volatility', 'FLOAT'),
            ('underlying_price_at_entry', 'FLOAT'),
            ('underlying_price_at_exit', 'FLOAT'),
            ('delta', 'FLOAT'),
            ('gamma', 'FLOAT'),
            ('theta', 'FLOAT'),
            ('vega', 'FLOAT')
        ]
        
        # Add options fields to Trade table
        for field_name, field_type in options_fields:
            try:
                with db.engine.connect() as conn:
                    conn.execute(db.text(f'ALTER TABLE trade ADD COLUMN {field_name} {field_type}'))
                    conn.commit()
                print(f"✅ Added {field_name} column to trade table")
            except Exception as e:
                print(f"⚠️  {field_name} column might already exist: {e}")
        
        # Add options_analysis field to TradeAnalysis table
        try:
            with db.engine.connect() as conn:
                conn.execute(db.text('ALTER TABLE trade_analysis ADD COLUMN options_analysis TEXT'))
                conn.commit()
            print("✅ Added options_analysis column to trade_analysis table")
        except Exception as e:
            print(f"⚠️  options_analysis column might already exist: {e}")
        
        print("\n🎉 Options trading migration completed!")
        print("📊 You can now add comprehensive options trades with:")
        print("   • Strike prices and expiration dates")
        print("   • Premium tracking and implied volatility")
        print("   • Underlying stock prices at entry/exit")
        print("   • Greeks (Delta, Gamma, Theta, Vega)")
        print("   • Options-specific AI analysis")

if __name__ == "__main__":
    print("🚀 Starting options trading database migration...")
    migrate_database() 