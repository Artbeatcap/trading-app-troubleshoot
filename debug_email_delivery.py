#!/usr/bin/env python3
"""
Debug script to pinpoint why market brief emails are not being sent.
This script will:
1. Check configuration values
2. Test SendGrid connectivity
3. Check user subscription status
4. Attempt to send a test email
5. Show detailed logging
"""

import os
import sys
from datetime import datetime
import logging

# Set up detailed logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Set up Flask app context
from app import app, db
from models import User, MarketBriefSubscriber
from emails import send_daily_brief_direct

def check_config():
    """Check email configuration"""
    print("\n=== EMAIL CONFIGURATION CHECK ===")
    
    with app.app_context():
        config_items = [
            'MAIL_SERVER',
            'MAIL_PORT', 
            'MAIL_USE_TLS',
            'MAIL_USE_SSL',
            'MAIL_USERNAME',
            'MAIL_DEFAULT_SENDER',
            'MAIL_SUPPRESS_SEND',
            'SENDGRID_KEY'
        ]
        
        for item in config_items:
            value = app.config.get(item)
            if item in ['MAIL_PASSWORD', 'SENDGRID_KEY'] and value:
                # Mask sensitive values
                value = f"{'*' * (len(str(value)) - 4)}{str(value)[-4:]}" if len(str(value)) > 4 else "***"
            print(f"  {item}: {value}")
        
        # Check environment variables
        print("\n=== ENVIRONMENT VARIABLES ===")
        env_vars = ['SENDGRID_KEY', 'MAIL_USERNAME', 'MAIL_PASSWORD', 'SERVER_NAME', 'PREFERRED_URL_SCHEME']
        for var in env_vars:
            value = os.getenv(var)
            if var in ['MAIL_PASSWORD', 'SENDGRID_KEY'] and value:
                value = f"{'*' * (len(value) - 4)}{value[-4:]}" if len(value) > 4 else "***"
            print(f"  {var}: {value}")

def check_users():
    """Check user subscription status"""
    print("\n=== USER SUBSCRIPTION STATUS ===")
    
    with app.app_context():
        # Count users by subscription status
        total_users = User.query.count()
        pro_users = User.query.filter(User.subscription_status.in_(['active', 'trialing'])).count()
        daily_subscribers = User.query.filter(User.is_subscribed_daily == True).count()
        
        print(f"  Total users: {total_users}")
        print(f"  Pro users (active/trialing): {pro_users}")
        print(f"  Users subscribed to daily: {daily_subscribers}")
        
        # Show first few pro users for verification
        pro_users_list = User.query.filter(
            User.subscription_status.in_(['active', 'trialing'])
        ).limit(5).all()
        
        print(f"\n  First {len(pro_users_list)} Pro users:")
        for user in pro_users_list:
            print(f"    {user.email}: status={user.subscription_status}, daily={user.is_subscribed_daily}")
        
        # Check MarketBriefSubscriber table
        total_subscribers = MarketBriefSubscriber.query.count()
        confirmed_subscribers = MarketBriefSubscriber.query.filter_by(confirmed=True).count()
        print(f"\n  MarketBriefSubscriber total: {total_subscribers}")
        print(f"  MarketBriefSubscriber confirmed: {confirmed_subscribers}")

def test_sendgrid():
    """Test SendGrid connectivity"""
    print("\n=== SENDGRID TEST ===")
    
    sendgrid_key = os.getenv('SENDGRID_KEY')
    if not sendgrid_key:
        print("  ❌ SENDGRID_KEY not found in environment")
        return False
    
    try:
        from sendgrid import SendGridAPIClient
        from sendgrid.helpers.mail import Mail as SGMail, Email as SGEmail, To as SGTo, Content as SGContent
        
        sg = SendGridAPIClient(api_key=sendgrid_key)
        
        # Test with a simple email to admin
        admin_email = os.getenv('ADMIN_EMAIL', 'clarencebellwork@gmail.com')
        
        from_email = SGEmail("support@optionsplunge.com", "Options Plunge Support")
        to_email = SGTo(admin_email)
        subject = f'SendGrid Test - {datetime.now().strftime("%Y-%m-%d %H:%M")}'
        content = SGContent("text/html", "<p>This is a SendGrid connectivity test.</p>")
        sg_mail = SGMail(from_email, to_email, subject, content)
        
        response = sg.send(sg_mail)
        
        if response.status_code in (200, 202):
            print(f"  ✅ SendGrid test successful (status: {response.status_code})")
            print(f"  Test email sent to: {admin_email}")
            return True
        else:
            print(f"  ❌ SendGrid test failed (status: {response.status_code})")
            print(f"  Response: {response.body}")
            return False
            
    except Exception as e:
        print(f"  ❌ SendGrid test failed with exception: {str(e)}")
        return False

def test_market_brief_send():
    """Test sending market brief to a single user"""
    print("\n=== MARKET BRIEF SEND TEST ===")
    
    with app.app_context():
        # Find a pro user to test with
        test_user = User.query.filter(
            User.subscription_status.in_(['active', 'trialing']),
            User.is_subscribed_daily == True
        ).first()
        
        if not test_user:
            print("  ❌ No Pro users found with daily subscription enabled")
            return False
        
        print(f"  Testing with user: {test_user.email}")
        
        # Create minimal test content
        test_html = """
        <h2>Test Market Brief</h2>
        <p>This is a test of the market brief delivery system.</p>
        <p>Generated at: {}</p>
        """.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        
        try:
            # Test the send_daily_brief_direct function with just this user
            success_count = send_daily_brief_direct(test_html)
            
            if success_count > 0:
                print(f"  ✅ Test brief sent successfully to {success_count} user(s)")
                return True
            else:
                print("  ❌ Test brief send returned 0 (no emails sent)")
                return False
                
        except Exception as e:
            print(f"  ❌ Test brief send failed with exception: {str(e)}")
            logger.exception("Full exception details:")
            return False

def main():
    """Run all diagnostic checks"""
    print("MARKET BRIEF EMAIL DELIVERY DIAGNOSTIC")
    print("=" * 50)
    
    check_config()
    check_users()
    
    sendgrid_ok = test_sendgrid()
    brief_ok = test_market_brief_send()
    
    print("\n=== SUMMARY ===")
    print(f"  SendGrid Test: {'✅ PASS' if sendgrid_ok else '❌ FAIL'}")
    print(f"  Brief Send Test: {'✅ PASS' if brief_ok else '❌ FAIL'}")
    
    if not sendgrid_ok and not brief_ok:
        print("\n❌ Both SendGrid and brief sending failed - check configuration")
    elif sendgrid_ok and not brief_ok:
        print("\n⚠️  SendGrid works but brief sending failed - check brief logic")
    elif not sendgrid_ok and brief_ok:
        print("\n⚠️  Brief sending worked but SendGrid test failed - using SMTP fallback")
    else:
        print("\n✅ All tests passed - email delivery should be working")

if __name__ == "__main__":
    main()
