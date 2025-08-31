#!/usr/bin/env python3
"""
Test script to diagnose billing issues on the live app
"""

import requests
import json
import os
from datetime import datetime

def test_billing_endpoints():
    """Test billing endpoints on the live app"""
    base_url = "https://optionsplunge.com"
    
    print("🔍 Testing Billing Endpoints on Live App")
    print("=" * 50)
    
    # Test 1: Pricing page
    print("\n1. Testing pricing page...")
    try:
        response = requests.get(f"{base_url}/api/billing/pricing", verify=False)
        print(f"   Status: {response.status_code}")
        if response.status_code == 200:
            print("   ✅ Pricing page accessible")
        else:
            print("   ❌ Pricing page not accessible")
    except Exception as e:
        print(f"   ❌ Error accessing pricing page: {e}")
    
    # Test 2: Checkout session creation (unauthenticated)
    print("\n2. Testing checkout session creation (unauthenticated)...")
    try:
        response = requests.post(
            f"{base_url}/api/billing/create-checkout-session",
            headers={"Content-Type": "application/json"},
            json={"plan": "monthly"},
            verify=False
        )
        print(f"   Status: {response.status_code}")
        if response.status_code in [302, 401]:
            print("   ✅ Properly redirecting to login (expected)")
        else:
            print("   ⚠️  Unexpected response")
    except Exception as e:
        print(f"   ❌ Error testing checkout session: {e}")
    
    # Test 3: Portal session creation (unauthenticated)
    print("\n3. Testing portal session creation (unauthenticated)...")
    try:
        response = requests.post(
            f"{base_url}/api/billing/create-portal-session",
            headers={"Content-Type": "application/json"},
            verify=False
        )
        print(f"   Status: {response.status_code}")
        if response.status_code in [302, 401]:
            print("   ✅ Properly redirecting to login (expected)")
        else:
            print("   ⚠️  Unexpected response")
    except Exception as e:
        print(f"   ❌ Error testing portal session: {e}")
    
    # Test 4: Settings page (unauthenticated)
    print("\n4. Testing settings page (unauthenticated)...")
    try:
        response = requests.get(f"{base_url}/settings", verify=False)
        print(f"   Status: {response.status_code}")
        if response.status_code == 302:
            print("   ✅ Properly redirecting to login (expected)")
        else:
            print("   ⚠️  Unexpected response")
    except Exception as e:
        print(f"   ❌ Error testing settings page: {e}")

def test_stripe_configuration():
    """Test Stripe configuration on the live app"""
    print("\n🔍 Testing Stripe Configuration")
    print("=" * 50)
    
    # Test 1: Check if Stripe environment variables are set
    print("\n1. Checking Stripe environment variables...")
    stripe_vars = [
        "STRIPE_SECRET_KEY",
        "STRIPE_PRICE_MONTHLY", 
        "STRIPE_PRICE_ANNUAL"
    ]
    
    for var in stripe_vars:
        value = os.getenv(var)
        if value:
            if "sk_" in value or "price_" in value:
                print(f"   ✅ {var}: Configured")
            else:
                print(f"   ⚠️  {var}: Set but may be invalid")
        else:
            print(f"   ❌ {var}: Not set")
    
    # Test 2: Test Stripe API connectivity
    print("\n2. Testing Stripe API connectivity...")
    try:
        import stripe
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        if stripe.api_key:
            # Test a simple API call
            account = stripe.Account.retrieve()
            print(f"   ✅ Stripe API connected (Account: {account.id})")
        else:
            print("   ❌ Stripe API key not configured")
    except ImportError:
        print("   ❌ Stripe library not installed")
    except Exception as e:
        print(f"   ❌ Stripe API error: {e}")

def test_billing_portal_configuration():
    """Test Stripe Customer Portal configuration"""
    print("\n🔍 Testing Stripe Customer Portal Configuration")
    print("=" * 50)
    
    try:
        import stripe
        stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
        
        if not stripe.api_key:
            print("   ❌ Stripe API key not configured")
            return
        
        # Test 1: Check if Customer Portal is configured
        print("\n1. Checking Customer Portal configuration...")
        try:
            # Try to create a test portal session
            session = stripe.billing_portal.Session.create(
                customer="cus_test",  # This will fail but show if portal is configured
                return_url="https://example.com"
            )
        except stripe.error.InvalidRequestError as e:
            if "billing_portal" in str(e).lower() or "configuration" in str(e).lower():
                print("   ❌ Customer Portal not configured in Stripe Dashboard")
                print("   💡 To fix: Go to Stripe Dashboard > Settings > Customer Portal")
            else:
                print(f"   ⚠️  Other Stripe error: {e}")
        except Exception as e:
            print(f"   ❌ Unexpected error: {e}")
            
    except ImportError:
        print("   ❌ Stripe library not available")
    except Exception as e:
        print(f"   ❌ Error testing portal configuration: {e}")

def main():
    """Main test function"""
    print(f"🚀 Billing System Diagnostic Test - {datetime.now()}")
    print("=" * 60)
    
    # Test billing endpoints
    test_billing_endpoints()
    
    # Test Stripe configuration
    test_stripe_configuration()
    
    # Test billing portal configuration
    test_billing_portal_configuration()
    
    print("\n" + "=" * 60)
    print("📋 Summary:")
    print("• If endpoints return 302/401 for unauthenticated requests: ✅ Working")
    print("• If Stripe API connects: ✅ Configuration valid")
    print("• If Customer Portal shows configuration error: ❌ Needs setup in Stripe Dashboard")
    print("\n🔧 Common Issues:")
    print("1. Stripe Customer Portal not configured in Stripe Dashboard")
    print("2. Invalid Stripe API keys")
    print("3. Missing environment variables")
    print("4. Network connectivity issues")

if __name__ == "__main__":
    main()

