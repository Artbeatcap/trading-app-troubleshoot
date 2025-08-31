#!/usr/bin/env python3
"""
Test script to verify the pricing setup is working correctly.
Run this after setting up Stripe to test the integration.
"""

import os
import sys
import requests
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_environment_variables():
    """Test that required environment variables are set"""
    print("🔍 Testing environment variables...")
    
    required_vars = [
        'STRIPE_SECRET_KEY',
        'STRIPE_PRICE_MONTHLY', 
        'STRIPE_PRICE_ANNUAL'
    ]
    
    optional_vars = [
        'STRIPE_WEBHOOK_SECRET'
    ]
    
    missing_required = []
    missing_optional = []
    
    for var in required_vars:
        if not os.getenv(var):
            missing_required.append(var)
    
    for var in optional_vars:
        if not os.getenv(var):
            missing_optional.append(var)
    
    if missing_required:
        print(f"❌ Missing required environment variables: {missing_required}")
        return False
    
    if missing_optional:
        print(f"⚠️  Missing optional environment variables: {missing_optional}")
    
    print("✅ All required environment variables are set")
    return True

def test_stripe_connection():
    """Test Stripe API connection"""
    print("\n🔍 Testing Stripe connection...")
    
    try:
        import stripe
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        
        # Test API connection by listing products
        products = stripe.Product.list(limit=1)
        print("✅ Stripe API connection successful")
        
        # Test price IDs
        monthly_price_id = os.getenv("STRIPE_PRICE_MONTHLY")
        annual_price_id = os.getenv("STRIPE_PRICE_ANNUAL")
        
        try:
            monthly_price = stripe.Price.retrieve(monthly_price_id)
            print(f"✅ Monthly price found: {monthly_price.unit_amount/100} {monthly_price.currency}")
        except Exception as e:
            print(f"❌ Monthly price not found: {e}")
            return False
        
        try:
            annual_price = stripe.Price.retrieve(annual_price_id)
            print(f"✅ Annual price found: {annual_price.unit_amount/100} {annual_price.currency}")
        except Exception as e:
            print(f"❌ Annual price not found: {e}")
            return False
        
        return True
        
    except ImportError:
        print("❌ Stripe library not installed. Run: pip install stripe")
        return False
    except Exception as e:
        print(f"❌ Stripe connection failed: {e}")
        return False

def test_database_migration():
    """Test that subscription fields exist in database"""
    print("\n🔍 Testing database migration...")
    
    try:
        from app import app, db
        from models import User
        
        with app.app_context():
            # Check if subscription columns exist
            inspector = db.inspect(db.engine)
            columns = [col['name'] for col in inspector.get_columns('user')]
            
            required_columns = [
                'subscription_status',
                'plan_type',
                'stripe_customer_id', 
                'stripe_subscription_id'
            ]
            
            missing_columns = [col for col in required_columns if col not in columns]
            
            if missing_columns:
                print(f"❌ Missing database columns: {missing_columns}")
                print("Run: python migrate_subscription_fields.py")
                return False
            
            print("✅ All subscription columns exist in database")
            
            # Test user model methods
            test_user = User()
            test_user.subscription_status = 'free'
            test_user.plan_type = 'none'
            
            if hasattr(test_user, 'has_pro_access'):
                result = test_user.has_pro_access()
                print(f"✅ User.has_pro_access() method works: {result}")
            else:
                print("❌ User.has_pro_access() method not found")
                return False
            
            return True
            
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False

def test_flask_routes():
    """Test that Flask routes are accessible"""
    print("\n🔍 Testing Flask routes...")
    
    try:
        from app import app
        
        with app.test_client() as client:
            # Test pricing page
            response = client.get('/pricing')
            if response.status_code == 200:
                print("✅ Pricing page accessible")
            else:
                print(f"❌ Pricing page returned status {response.status_code}")
                return False
            
            # Test billing API endpoint (should return 401 for unauthenticated)
            response = client.post('/api/billing/create-checkout-session', 
                                 json={'plan': 'monthly'})
            if response.status_code == 401:
                print("✅ Billing API properly protected (requires authentication)")
            else:
                print(f"⚠️  Billing API returned unexpected status {response.status_code}")
            
            return True
            
    except Exception as e:
        print(f"❌ Flask routes test failed: {e}")
        return False

def test_billing_module():
    """Test billing module imports and functions"""
    print("\n🔍 Testing billing module...")
    
    try:
        from billing import bp, requires_pro
        print("✅ Billing blueprint imported successfully")
        print("✅ requires_pro decorator imported successfully")
        return True
    except ImportError as e:
        print(f"❌ Billing module import failed: {e}")
        return False

def main():
    """Run all tests"""
    print("🚀 Options Plunge Pricing Setup Test")
    print("=" * 50)
    
    tests = [
        ("Environment Variables", test_environment_variables),
        ("Stripe Connection", test_stripe_connection),
        ("Database Migration", test_database_migration),
        ("Flask Routes", test_flask_routes),
        ("Billing Module", test_billing_module)
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        try:
            if test_func():
                passed += 1
        except Exception as e:
            print(f"❌ {test_name} test failed with exception: {e}")
    
    print("\n" + "=" * 50)
    print(f"📊 Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Your pricing setup is ready.")
        print("\nNext steps:")
        print("1. Start your Flask app: python app.py")
        print("2. Visit http://localhost:5000/pricing")
        print("3. Test the checkout flow with Stripe test cards")
    else:
        print("⚠️  Some tests failed. Please check the setup guide.")
        print("\nSee STRIPE_PRICING_SETUP.md for detailed instructions.")

if __name__ == "__main__":
    main()

