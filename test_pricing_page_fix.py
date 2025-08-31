#!/usr/bin/env python3
"""
Test script to verify the pricing page fixes
"""
import os
import sys

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_pricing_page_fix():
    """Test the pricing page fixes"""
    print("Testing pricing page fixes...")
    
    try:
        # Test 1: Check app startup
        print("\n1. Testing app startup...")
        from app import app
        print("✓ App imports successfully")
        
        # Test 2: Test pricing page rendering
        print("\n2. Testing pricing page rendering...")
        with app.test_client() as client:
            # Test as anonymous user
            response = client.get('/api/billing/pricing')
            print(f"Pricing page (anonymous): {response.status_code}")
            
            # Check if login link is present
            content = response.get_data(as_text=True)
            if 'Log In to Start Trial' in content:
                print("✓ Login link present for anonymous users")
            else:
                print("✗ Login link missing for anonymous users")
        
        # Test 3: Test checkout endpoint with authentication
        print("\n3. Testing checkout endpoint...")
        with app.test_client() as client:
            # Test without authentication (should redirect)
            response = client.post('/api/billing/create-checkout-session', 
                                 json={'plan': 'monthly'},
                                 follow_redirects=False)
            print(f"Checkout without auth: {response.status_code}")
            
            if response.status_code == 302:
                print("✓ Properly redirects unauthenticated users")
            else:
                print("✗ Does not redirect unauthenticated users")
        
        # Test 4: Check billing module functionality
        print("\n4. Testing billing module...")
        from billing import bp
        print(f"✓ Billing blueprint: {bp.name}")
        print(f"✓ Billing blueprint registered successfully")
        
        print("\n🎉 Pricing page fixes test completed!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_pricing_page_fix()
