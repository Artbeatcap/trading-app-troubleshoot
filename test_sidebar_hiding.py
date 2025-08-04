#!/usr/bin/env python3
"""
Test script to verify sidebar hiding functionality
"""

import requests
import time

def test_sidebar_hiding():
    """Test that sidebar is hidden on landing page and visible on other pages"""
    
    base_url = "http://localhost:5000"
    
    print("Testing sidebar hiding functionality...")
    print("=" * 50)
    
    # Test 1: Landing page (/) - should hide sidebar
    print("1. Testing landing page (/)...")
    try:
        response = requests.get(f"{base_url}/", timeout=5)
        if response.status_code == 200:
            if 'hide_sidebar' in response.text or 'sidebar' not in response.text:
                print("   ✓ Landing page correctly hides sidebar")
            else:
                print("   ✗ Landing page shows sidebar (should be hidden)")
        else:
            print(f"   ✗ Landing page returned status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"   ✗ Could not connect to landing page: {e}")
    
    # Test 2: Dashboard page (/dashboard) - should show sidebar
    print("2. Testing dashboard page (/dashboard)...")
    try:
        response = requests.get(f"{base_url}/dashboard", timeout=5)
        if response.status_code == 200:
            if 'sidebar' in response.text and 'hide_sidebar' not in response.text:
                print("   ✓ Dashboard page correctly shows sidebar")
            else:
                print("   ✗ Dashboard page hides sidebar (should be shown)")
        else:
            print(f"   ✗ Dashboard page returned status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"   ✗ Could not connect to dashboard page: {e}")
    
    # Test 3: Login page (/login) - should hide sidebar
    print("3. Testing login page (/login)...")
    try:
        response = requests.get(f"{base_url}/login", timeout=5)
        if response.status_code == 200:
            if 'hide_sidebar' in response.text or 'sidebar' not in response.text:
                print("   ✓ Login page correctly hides sidebar")
            else:
                print("   ✗ Login page shows sidebar (should be hidden)")
        else:
            print(f"   ✗ Login page returned status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"   ✗ Could not connect to login page: {e}")
    
    print("=" * 50)
    print("Test completed!")

if __name__ == "__main__":
    print("Make sure the Flask app is running on http://localhost:5000")
    print("Press Enter to start testing...")
    input()
    test_sidebar_hiding() 