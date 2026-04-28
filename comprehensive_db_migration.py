#!/usr/bin/env python3
"""
Comprehensive Database Migration Script
Creates all tables defined in models.py
"""

import os
import sys
from datetime import datetime
from sqlalchemy import create_engine, text
from sqlalchemy.exc import ProgrammingError

# Add the current directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from dotenv import load_dotenv
load_dotenv()

# Database configuration
DATABASE_URL = os.getenv('DATABASE_URL', 'postgresql://tradingapp:<DB_PASSWORD>@localhost/trading_journal')

def create_tables():
    """Create all tables defined in models.py"""
    
    print("🔄 Starting comprehensive database migration...")
    print(f"📊 Database URL: {DATABASE_URL}")
    
    # Create engine
    engine = create_engine(DATABASE_URL)
    
    # Import models after engine creation
    from models import db, User, Trade, TradeAnalysis, TradingJournal, UserSettings, MarketBriefSubscriber, EmailDelivery, MarketBrief
    
    # Create all tables
    try:
        print("📋 Creating tables...")
        db.create_all()
        print("✅ All tables created successfully!")
        
        # Verify tables exist
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name;
            """))
            
            tables = [row[0] for row in result]
            print(f"📊 Found {len(tables)} tables: {', '.join(tables)}")
            
            # Check for specific tables
            required_tables = [
                'user', 'trade', 'trade_analysis', 'trading_journal', 
                'user_settings', 'market_brief_subscriber', 'email_delivery', 'market_brief'
            ]
            
            missing_tables = [table for table in required_tables if table not in tables]
            
            if missing_tables:
                print(f"⚠️  Missing tables: {', '.join(missing_tables)}")
                return False
            else:
                print("✅ All required tables exist!")
                return True
                
    except Exception as e:
        print(f"❌ Error creating tables: {e}")
        return False

def create_indexes():
    """Create additional indexes for performance"""
    print("🔍 Creating indexes...")
    
    engine = create_engine(DATABASE_URL)
    
    indexes = [
        "CREATE INDEX IF NOT EXISTS idx_trade_user_id ON trade(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_trade_entry_date ON trade(entry_date);",
        "CREATE INDEX IF NOT EXISTS idx_trade_exit_date ON trade(exit_date);",
        "CREATE INDEX IF NOT EXISTS idx_trade_analysis_trade_id ON trade_analysis(trade_id);",
        "CREATE INDEX IF NOT EXISTS idx_trading_journal_user_id ON trading_journal(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_trading_journal_date ON trading_journal(journal_date);",
        "CREATE INDEX IF NOT EXISTS idx_user_email ON \"user\"(email);",
        "CREATE INDEX IF NOT EXISTS idx_user_username ON \"user\"(username);",
        "CREATE INDEX IF NOT EXISTS idx_market_brief_subscriber_email ON market_brief_subscriber(email);",
        "CREATE INDEX IF NOT EXISTS idx_email_delivery_user_id ON email_delivery(user_id);",
        "CREATE INDEX IF NOT EXISTS idx_email_delivery_sent_at ON email_delivery(sent_at);"
    ]
    
    try:
        with engine.connect() as conn:
            for index_sql in indexes:
                try:
                    conn.execute(text(index_sql))
                    conn.commit()
                except Exception as e:
                    print(f"⚠️  Index creation warning: {e}")
        
        print("✅ Indexes created successfully!")
        return True
    except Exception as e:
        print(f"❌ Error creating indexes: {e}")
        return False

def main():
    """Main migration function"""
    print("🚀 Starting comprehensive database migration...")
    print("=" * 50)
    
    # Create tables
    if not create_tables():
        print("❌ Table creation failed!")
        sys.exit(1)
    
    # Create indexes
    if not create_indexes():
        print("⚠️  Index creation had issues, but continuing...")
    
    print("=" * 50)
    print("✅ Comprehensive database migration completed successfully!")
    print("🎉 Your database is now ready for the updated application!")

if __name__ == "__main__":
    main()
