#!/usr/bin/env python3
"""
Check billing routes and authentication
"""

import requests
import json

def test_billing_authentication():
    """Test billing authentication"""
    base_url = "https://optionsplunge.com"
    
    print("🔍 Testing Billing Authentication")
    print("=" * 40)
    
    # Test billing endpoints
    endpoints = [
        "/api/billing/create-checkout-session",
        "/api/billing/create-portal-session",
        "/api/billing/sync"
    ]
    
    for endpoint in endpoints:
        print(f"\nTesting {endpoint}...")
        try:
            response = requests.post(
                f"{base_url}{endpoint}",
                headers={"Content-Type": "application/json"},
                json={},
                verify=False,
                allow_redirects=False
            )
            print(f"  Status: {response.status_code}")
            print(f"  Location: {response.headers.get('Location', 'None')}")
            
            if response.status_code == 302:
                location = response.headers.get('Location', '')
                if 'login' in location:
                    print("  ✅ Properly redirecting to login")
                else:
                    print("  ⚠️  Redirecting but not to login")
            elif response.status_code == 401:
                print("  ✅ Properly returning 401 Unauthorized")
            else:
                print("  ❌ Unexpected response")
                print(f"  Content: {response.text[:200]}...")
                
        except Exception as e:
            print(f"  ❌ Error: {e}")

if __name__ == "__main__":
    test_billing_authentication()

