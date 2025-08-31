#!/usr/bin/env python3
"""
Script to upgrade admin user to Pro status for testing
"""

import os
import sys
from app import app, db
from models import User

def upgrade_admin_to_pro():
    """Upgrade admin user to Pro status"""
    with app.app_context():
        # Find admin user
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            print("❌ Admin user not found! Run create_admin.py first.")
            return
        
        # Upgrade to Pro
        admin.subscription_status = "active"
        admin.plan_type = "monthly"  # or "annual"
        admin.is_subscribed_daily = True  # Enable daily brief
        admin.is_subscribed_weekly = True  # Enable weekly brief
        
        # Add some test data
        admin.account_size = 100000  # $100k account for testing
        admin.default_risk_percent = 2.0
        
        # Commit changes
        db.session.commit()
        
        print("✅ Admin user upgraded to Pro successfully!")
        print(f"Username: {admin.username}")
        print(f"Email: {admin.email}")
        print(f"Subscription Status: {admin.subscription_status}")
        print(f"Plan Type: {admin.plan_type}")
        print(f"Daily Brief: {admin.is_subscribed_daily}")
        print(f"Weekly Brief: {admin.is_subscribed_weekly}")
        print(f"Account Size: ${admin.account_size:,.0f}")
        print(f"Default Risk: {admin.default_risk_percent}%")

def downgrade_admin_to_free():
    """Downgrade admin user back to free status"""
    with app.app_context():
        # Find admin user
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            print("❌ Admin user not found!")
            return
        
        # Downgrade to free
        admin.subscription_status = "free"
        admin.plan_type = "none"
        admin.is_subscribed_daily = False
        admin.is_subscribed_weekly = True  # Keep weekly (free for all)
        
        # Commit changes
        db.session.commit()
        
        print("✅ Admin user downgraded to free successfully!")
        print(f"Username: {admin.username}")
        print(f"Subscription Status: {admin.subscription_status}")
        print(f"Daily Brief: {admin.is_subscribed_daily}")
        print(f"Weekly Brief: {admin.is_subscribed_weekly}")

def show_admin_status():
    """Show current admin user status"""
    with app.app_context():
        # Find admin user
        admin = User.query.filter_by(username='admin').first()
        if not admin:
            print("❌ Admin user not found! Run create_admin.py first.")
            return
        
        print("📊 Admin User Status:")
        print(f"Username: {admin.username}")
        print(f"Email: {admin.email}")
        print(f"Subscription Status: {admin.subscription_status}")
        print(f"Plan Type: {admin.plan_type}")
        print(f"Daily Brief: {admin.is_subscribed_daily}")
        print(f"Weekly Brief: {admin.is_subscribed_weekly}")
        print(f"Account Size: ${admin.account_size or 0:,.0f}")
        print(f"Default Risk: {admin.default_risk_percent or 0}%")
        print(f"Email Verified: {admin.email_verified}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == "upgrade" or command == "pro":
            upgrade_admin_to_pro()
        elif command == "downgrade" or command == "free":
            downgrade_admin_to_free()
        elif command == "status":
            show_admin_status()
        else:
            print("Usage: python upgrade_admin_to_pro.py [upgrade|downgrade|status]")
    else:
        print("🔧 Admin Pro Testing Tool")
        print("Usage:")
        print("  python upgrade_admin_to_pro.py upgrade  - Upgrade admin to Pro")
        print("  python upgrade_admin_to_pro.py downgrade - Downgrade admin to free")
        print("  python upgrade_admin_to_pro.py status   - Show current status")
        print()
        show_admin_status()
