#!/usr/bin/env python3
"""
Database initialization script for Options Plunge
Run this script to create the database tables.
"""

from app import app, db
from models import User, Trade, TradeAnalysis, TradingJournal, UserSettings

def init_db():
    with app.app_context():
        # Drop all tables first
        db.drop_all()
        
        # Create all tables
        db.create_all()
        
        # Create a test user if none exists
        if not User.query.first():
            test_user = User(
                username='test',
                email='test@example.com',
                account_size=10000,
                default_risk_percent=1.0
            )
            test_user.set_password('password')
            db.session.add(test_user)
            db.session.flush()  # Flush to get the user ID
            
            # Create settings for test user
            settings = UserSettings(
                user_id=test_user.id,
                auto_analyze_trades=True,
                daily_journal_reminder=True,
                weekly_summary=True,
                default_chart_timeframe='1D',
                trades_per_page=20,
                default_risk_percent=2.0
            )
            db.session.add(settings)
            
            db.session.commit()
            print("Created test user with username 'test' and password 'password'")

if __name__ == '__main__':
    print("🚀 Initializing Options Plunge Database...")
    init_db()
    print("\n🎉 Database initialization complete!")
    print("\nNext steps:")
    print("1. Run the application with 'python app.py'")
    print("2. Log in with username 'test' and password 'password'")
    print("3. Set up your .env file with OpenAI API key")
    print("4. Register a new account and start trading analysis!") 