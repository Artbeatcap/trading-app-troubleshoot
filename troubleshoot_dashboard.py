#!/usr/bin/env python3
"""
Dashboard Troubleshooting Script
This script helps identify the cause of the 500 error on the dashboard route.
"""

import os
import sys
import traceback
from datetime import date

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_imports():
    """Test if all required modules can be imported"""
    print("Testing imports...")
    
    try:
        from flask import Flask
        print("✓ Flask imported successfully")
    except ImportError as e:
        print(f"✗ Flask import failed: {e}")
        return False
    
    try:
        from flask_login import current_user
        print("✓ Flask-Login imported successfully")
    except ImportError as e:
        print(f"✗ Flask-Login import failed: {e}")
        return False
    
    try:
        from models import db, User, Trade, TradingJournal
        print("✓ Models imported successfully")
    except ImportError as e:
        print(f"✗ Models import failed: {e}")
        return False
    
    try:
        from config import Config
        print("✓ Config imported successfully")
    except ImportError as e:
        print(f"✗ Config import failed: {e}")
        return False
    
    return True

def test_database_connection():
    """Test database connection"""
    print("\nTesting database connection...")
    
    try:
        from app import app, db
        from models import User, Trade, TradingJournal
        
        with app.app_context():
            # Test basic database operations using newer SQLAlchemy syntax
            with db.engine.connect() as conn:
                result = conn.execute(db.text("SELECT 1"))
                print("✓ Database connection successful")
            
            # Test User table
            user_count = User.query.count()
            print(f"✓ User table accessible, {user_count} users found")
            
            # Test Trade table
            trade_count = Trade.query.count()
            print(f"✓ Trade table accessible, {trade_count} trades found")
            
            # Test TradingJournal table
            journal_count = TradingJournal.query.count()
            print(f"✓ TradingJournal table accessible, {journal_count} journals found")
            
            return True
            
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        print(f"Error type: {type(e).__name__}")
        traceback.print_exc()
        return False

def test_dashboard_queries():
    """Test the specific queries used in the dashboard route"""
    print("\nTesting dashboard queries...")
    
    try:
        from app import app, db
        from models import User, Trade, TradingJournal
        from datetime import date
        
        with app.app_context():
            # Test if there are any users
            users = User.query.all()
            if not users:
                print("⚠ No users found in database")
                return True
            
            # Test with first user
            user = users[0]
            print(f"✓ Testing with user: {user.username}")
            
            # Test get_recent_trades
            try:
                recent_trades = user.get_recent_trades(10)
                print(f"✓ get_recent_trades successful, {len(recent_trades)} trades returned")
            except Exception as e:
                print(f"✗ get_recent_trades failed: {e}")
                return False
            
            # Test get_win_rate
            try:
                win_rate = user.get_win_rate()
                print(f"✓ get_win_rate successful: {win_rate}%")
            except Exception as e:
                print(f"✗ get_win_rate failed: {e}")
                return False
            
            # Test get_total_pnl
            try:
                total_pnl = user.get_total_pnl()
                print(f"✓ get_total_pnl successful: ${total_pnl}")
            except Exception as e:
                print(f"✗ get_total_pnl failed: {e}")
                return False
            
            # Test Trade queries
            try:
                total_trades = Trade.query.filter_by(user_id=user.id).count()
                print(f"✓ Trade count query successful: {total_trades}")
            except Exception as e:
                print(f"✗ Trade count query failed: {e}")
                return False
            
            try:
                analyzed_trades = Trade.query.filter_by(user_id=user.id, is_analyzed=True).count()
                print(f"✓ Analyzed trades query successful: {analyzed_trades}")
            except Exception as e:
                print(f"✗ Analyzed trades query failed: {e}")
                return False
            
            # Test TradingJournal queries
            try:
                recent_journals = TradingJournal.query.filter_by(user_id=user.id).order_by(TradingJournal.journal_date.desc()).limit(5).all()
                print(f"✓ Recent journals query successful: {len(recent_journals)} journals")
            except Exception as e:
                print(f"✗ Recent journals query failed: {e}")
                return False
            
            try:
                today_journal = TradingJournal.query.filter_by(user_id=user.id, journal_date=date.today()).first()
                print(f"✓ Today's journal query successful: {'Found' if today_journal else 'Not found'}")
            except Exception as e:
                print(f"✗ Today's journal query failed: {e}")
                return False
            
            return True
            
    except Exception as e:
        print(f"✗ Dashboard queries test failed: {e}")
        traceback.print_exc()
        return False

def test_guest_dashboard():
    """Test dashboard queries for non-authenticated users"""
    print("\nTesting guest dashboard queries...")
    
    try:
        from app import app, db
        from models import Trade, TradingJournal
        
        with app.app_context():
            # Test recent trades for guests
            try:
                recent_trades = Trade.query.order_by(Trade.entry_date.desc()).limit(10).all()
                print(f"✓ Guest recent trades query successful: {len(recent_trades)} trades")
            except Exception as e:
                print(f"✗ Guest recent trades query failed: {e}")
                return False
            
            # Test closed trades for win rate calculation
            try:
                closed_trades = Trade.query.filter(Trade.exit_price.isnot(None)).all()
                print(f"✓ Guest closed trades query successful: {len(closed_trades)} trades")
                
                if closed_trades:
                    win_rate = len([t for t in closed_trades if t.profit_loss and t.profit_loss > 0]) / len(closed_trades) * 100
                    print(f"✓ Win rate calculation successful: {win_rate}%")
                else:
                    print("✓ No closed trades found, win rate would be 0%")
            except Exception as e:
                print(f"✗ Guest win rate calculation failed: {e}")
                return False
            
            # Test total P&L calculation
            try:
                total_pnl = sum(t.profit_loss for t in closed_trades if t.profit_loss)
                print(f"✓ Guest total P&L calculation successful: ${total_pnl}")
            except Exception as e:
                print(f"✗ Guest total P&L calculation failed: {e}")
                return False
            
            # Test guest journal queries
            try:
                recent_journals = TradingJournal.query.order_by(TradingJournal.journal_date.desc()).limit(5).all()
                print(f"✓ Guest recent journals query successful: {len(recent_journals)} journals")
            except Exception as e:
                print(f"✗ Guest recent journals query failed: {e}")
                return False
            
            return True
            
    except Exception as e:
        print(f"✗ Guest dashboard test failed: {e}")
        traceback.print_exc()
        return False

def test_environment():
    """Test environment variables and configuration"""
    print("\nTesting environment configuration...")
    
    try:
        from config import Config
        
        # Check database URL
        db_url = os.environ.get('DATABASE_URL', Config.SQLALCHEMY_DATABASE_URI)
        print(f"✓ Database URL: {db_url}")
        
        # Check if it's a PostgreSQL URL
        if 'postgresql' in db_url:
            print("✓ Using PostgreSQL database")
        else:
            print("⚠ Using SQLite database (not recommended for production)")
        
        # Check other important environment variables
        secret_key = os.environ.get('SECRET_KEY')
        if secret_key and secret_key != 'trading-analysis-secret-key-change-in-production':
            print("✓ SECRET_KEY is set")
        else:
            print("⚠ SECRET_KEY not set or using default")
        
        openai_key = os.environ.get('OPENAI_API_KEY')
        if openai_key:
            print("✓ OPENAI_API_KEY is set")
        else:
            print("⚠ OPENAI_API_KEY not set")
        
        tradier_token = os.environ.get('TRADIER_API_TOKEN')
        if tradier_token:
            print("✓ TRADIER_API_TOKEN is set")
        else:
            print("⚠ TRADIER_API_TOKEN not set")
        
        return True
        
    except Exception as e:
        print(f"✗ Environment test failed: {e}")
        return False

def main():
    """Run all tests"""
    print("Dashboard Troubleshooting Script")
    print("=" * 40)
    
    # Test imports
    if not test_imports():
        print("\n❌ Import tests failed. Please check your dependencies.")
        return
    
    # Test environment
    if not test_environment():
        print("\n❌ Environment test failed.")
        return
    
    # Test database connection
    if not test_database_connection():
        print("\n❌ Database connection failed. Please check your database configuration.")
        return
    
    # Test dashboard queries
    if not test_dashboard_queries():
        print("\n❌ Dashboard queries failed. This is likely the cause of the 500 error.")
        return
    
    # Test guest dashboard
    if not test_guest_dashboard():
        print("\n❌ Guest dashboard queries failed.")
        return
    
    print("\n✅ All tests passed! The dashboard should work correctly.")
    print("\nIf you're still getting 500 errors, check:")
    print("1. Gunicorn logs: sudo journalctl -u trading-analysis -f")
    print("2. Nginx logs: sudo tail -f /var/log/nginx/error.log")
    print("3. Database permissions and connectivity")

if __name__ == "__main__":
    main() 