#!/usr/bin/env python3
"""
Test script to debug pricing page checkout issues
"""
import os
import sys
import requests
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_pricing_page():
    """Test the pricing page functionality"""
    print("Testing pricing page checkout functionality...")
    
    try:
        # Test 1: Check if app can start
        print("\n1. Testing app startup...")
        from app import app
        print("✓ App imports successfully")
        
        # Test 2: Check billing routes
        print("\n2. Testing billing routes...")
        with app.test_client() as client:
            # Test pricing page
            response = client.get('/api/billing/pricing')
            print(f"Pricing page status: {response.status_code}")
            
            # Test checkout endpoint (should fail without auth)
            response = client.post('/api/billing/create-checkout-session', 
                                 json={'plan': 'monthly'})
            print(f"Checkout endpoint status (no auth): {response.status_code}")
            print(f"Checkout response: {response.get_json()}")
            
        # Test 3: Check if billing blueprint is registered
        print("\n3. Testing blueprint registration...")
        billing_routes = [rule.rule for rule in app.url_map.iter_rules() 
                         if 'billing' in rule.rule]
        print(f"Billing routes found: {billing_routes}")
        
        # Test 4: Check environment variables
        print("\n4. Testing environment variables...")
        stripe_key = os.getenv('STRIPE_SECRET_KEY')
        stripe_monthly = os.getenv('STRIPE_PRICE_MONTHLY')
        stripe_annual = os.getenv('STRIPE_PRICE_ANNUAL')
        
        print(f"Stripe key exists: {bool(stripe_key)}")
        print(f"Monthly price ID: {stripe_monthly}")
        print(f"Annual price ID: {stripe_annual}")
        
        # Test 5: Check billing module
        print("\n5. Testing billing module...")
        from billing import bp, create_checkout_session, create_portal_session
        print("✓ Billing module imports successfully")
        print(f"Billing blueprint name: {bp.name}")
        print(f"Billing blueprint url_prefix: {bp.url_prefix}")
        
        print("\n🎉 All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pricing_page()
