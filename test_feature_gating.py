#!/usr/bin/env python3
"""
Test script to verify feature gating implementation
"""

import requests
import json

def test_feature_gating():
    """Test the feature gating implementation"""
    base_url = "http://localhost:5000"
    
    print("🧪 Testing Feature Gating Implementation")
    print("=" * 50)
    
    # Test 1: Pro pages should be accessible in preview mode
    print("\n1. Testing Pro page preview access...")
    
    pro_pages = [
        "/bulk_analysis",
        "/market_brief", 
        "/tools/options-calculator"
    ]
    
    for page in pro_pages:
        try:
            response = requests.get(f"{base_url}{page}")
            if response.status_code == 200:
                print(f"✅ {page} - Accessible (preview mode)")
            else:
                print(f"❌ {page} - Status {response.status_code}")
        except Exception as e:
            print(f"❌ {page} - Error: {e}")
    
    # Test 2: Pro pages with preview parameter
    print("\n2. Testing Pro pages with preview parameter...")
    
    for page in pro_pages:
        try:
            response = requests.get(f"{base_url}{page}?preview=1")
            if response.status_code == 200:
                print(f"✅ {page}?preview=1 - Accessible")
            else:
                print(f"❌ {page}?preview=1 - Status {response.status_code}")
        except Exception as e:
            print(f"❌ {page}?preview=1 - Error: {e}")
    
    # Test 3: Pro API endpoints should be protected
    print("\n3. Testing Pro API endpoint protection...")
    
    pro_apis = [
        ("/api/quick_trade", {"symbol": "AAPL", "trade_type": "long", "entry_price": 150.0, "quantity": 100}),
        ("/tools/options-pnl", {"option_type": "call", "strike": 150, "current_price": 155, "expiration_date": "2024-01-19", "premium": 5.0}),
        ("/tools/calculate-bs", {"option_type": "call", "stock_price": 150, "strike_price": 155, "time_to_expiry": 0.25, "risk_free_rate": 0.05, "volatility": 0.3})
    ]
    
    for endpoint, data in pro_apis:
        try:
            response = requests.post(f"{base_url}{endpoint}", json=data)
            if response.status_code in [401, 402]:
                print(f"✅ {endpoint} - Properly protected (status {response.status_code})")
            else:
                print(f"⚠️  {endpoint} - Unexpected status {response.status_code}")
        except Exception as e:
            print(f"❌ {endpoint} - Error: {e}")
    
    # Test 4: Check if Pro upsell partial is included
    print("\n4. Testing Pro upsell partial inclusion...")
    
    for page in pro_pages:
        try:
            response = requests.get(f"{base_url}{page}")
            if response.status_code == 200:
                if "show_pro_upsell" in response.text or "Pro Preview" in response.text:
                    print(f"✅ {page} - Pro upsell included")
                else:
                    print(f"⚠️  {page} - Pro upsell not found")
            else:
                print(f"❌ {page} - Status {response.status_code}")
        except Exception as e:
            print(f"❌ {page} - Error: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Feature Gating Test Complete!")
    print("\nManual Testing Checklist:")
    print("• Visit /bulk_analysis as non-Pro user - should see preview + upsell")
    print("• Visit /market_brief as non-Pro user - should see preview + upsell") 
    print("• Visit /tools/options-calculator as non-Pro user - should see demo data + upsell")
    print("• Try to submit forms on Pro pages - should be disabled in preview mode")
    print("• Check navigation - Pro links should have lock icons")
    print("• Test ?preview=1 parameter on any Pro page")

if __name__ == "__main__":
    test_feature_gating()


