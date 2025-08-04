#!/usr/bin/env python3
"""
Simplified test script for the newsletter system (no external APIs)
"""
import os
import sys
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import app, db
from models import MarketBriefSubscriber
from emails import send_confirmation_email, send_welcome_email

def test_basic_functionality():
    """Test basic newsletter functionality without external APIs"""
    print("🧪 Testing Basic Newsletter Functionality")
    print("=" * 50)
    
    with app.app_context():
        # Test 1: Create a test subscriber
        print("\n1. Creating test subscriber...")
        test_email = f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}@example.com"
        subscriber = MarketBriefSubscriber(
            name="Test User",
            email=test_email,
            confirmed=False
        )
        db.session.add(subscriber)
        db.session.commit()
        print(f"✅ Created subscriber: {test_email}")
        
        # Test 2: Generate confirmation token
        print("\n2. Generating confirmation token...")
        token = subscriber.generate_confirmation_token()
        db.session.commit()
        print(f"✅ Generated token: {token[:10]}...")
        
        # Test 3: Send confirmation email
        print("\n3. Sending confirmation email...")
        if send_confirmation_email(subscriber):
            print("✅ Confirmation email sent successfully")
        else:
            print("❌ Failed to send confirmation email")
        
        # Test 4: Confirm subscription
        print("\n4. Confirming subscription...")
        subscriber.confirm_subscription()
        db.session.commit()
        print("✅ Subscription confirmed")
        
        # Test 5: Send welcome email
        print("\n5. Sending welcome email...")
        if send_welcome_email(subscriber):
            print("✅ Welcome email sent successfully")
        else:
            print("❌ Failed to send welcome email")
        
        # Test 6: Check subscriber status
        print("\n6. Checking subscriber status...")
        confirmed_subscribers = MarketBriefSubscriber.query.filter_by(confirmed=True, is_active=True).all()
        print(f"✅ Found {len(confirmed_subscribers)} confirmed active subscribers")
        
        # Test 7: Test unsubscribe functionality
        print("\n7. Testing unsubscribe...")
        subscriber.unsubscribe()
        db.session.commit()
        active_subscribers = MarketBriefSubscriber.query.filter_by(confirmed=True, is_active=True).all()
        print(f"✅ After unsubscribe: {len(active_subscribers)} active subscribers")
        
        # Cleanup
        print("\n8. Cleaning up test data...")
        db.session.delete(subscriber)
        db.session.commit()
        print("✅ Test subscriber removed")
        
        print("\n🎉 All basic tests completed!")

def test_email_templates():
    """Test email template rendering"""
    print("\n🧪 Testing Email Templates")
    print("=" * 50)
    
    with app.app_context():
        from flask import render_template
        
        # Test confirmation template
        print("\n1. Testing confirmation email template...")
        try:
            html = render_template('email/confirm_brief.html', 
                                 name="Test User", 
                                 url="https://example.com/confirm/test")
            print("✅ Confirmation template renders successfully")
            print(f"   Template length: {len(html)} characters")
        except Exception as e:
            print(f"❌ Confirmation template error: {str(e)}")
        
        # Test daily brief template
        print("\n2. Testing daily brief email template...")
        try:
            html = render_template('email/daily_brief.html',
                                 content="<p>Test content</p>",
                                 date="2024-01-01",
                                 unsubscribe_url="https://example.com/unsubscribe",
                                 preferences_url="https://example.com/preferences")
            print("✅ Daily brief template renders successfully")
            print(f"   Template length: {len(html)} characters")
        except Exception as e:
            print(f"❌ Daily brief template error: {str(e)}")
        
        # Test welcome template
        print("\n3. Testing welcome email template...")
        try:
            html = render_template('email/welcome_brief.html', name="Test User")
            print("✅ Welcome template renders successfully")
            print(f"   Template length: {len(html)} characters")
        except Exception as e:
            print(f"❌ Welcome template error: {str(e)}")

def show_subscriber_stats():
    """Show current subscriber statistics"""
    print("\n📊 Current Subscriber Statistics")
    print("=" * 50)
    
    with app.app_context():
        total = MarketBriefSubscriber.query.count()
        confirmed = MarketBriefSubscriber.query.filter_by(confirmed=True).count()
        active = MarketBriefSubscriber.query.filter_by(confirmed=True, is_active=True).count()
        unconfirmed = MarketBriefSubscriber.query.filter_by(confirmed=False).count()
        
        print(f"Total subscribers: {total}")
        print(f"Confirmed subscribers: {confirmed}")
        print(f"Active subscribers: {active}")
        print(f"Unconfirmed subscribers: {unconfirmed}")
        
        if total > 0:
            print(f"\nRecent subscribers:")
            recent = MarketBriefSubscriber.query.order_by(MarketBriefSubscriber.subscribed_at.desc()).limit(5).all()
            for sub in recent:
                status = "✅ Confirmed" if sub.confirmed else "⏳ Pending"
                active_status = "🟢 Active" if sub.is_active else "🔴 Inactive"
                print(f"  {sub.email} - {sub.name} - {status} - {active_status}")

if __name__ == "__main__":
    print("🚀 Simplified Newsletter System Test Suite")
    print("=" * 50)
    
    # Check if we're in a Flask app context
    try:
        with app.app_context():
            pass
    except Exception as e:
        print(f"❌ Error initializing Flask app: {str(e)}")
        print("Make sure your environment variables are set correctly")
        sys.exit(1)
    
    # Run tests
    test_email_templates()
    show_subscriber_stats()
    test_basic_functionality()
    
    print("\n✨ Simplified test suite completed!") 