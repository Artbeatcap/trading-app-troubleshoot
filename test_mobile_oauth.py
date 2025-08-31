#!/usr/bin/env python3
"""
Test script for mobile OAuth functionality
This script helps verify that Google OAuth works properly on mobile devices
"""

import requests
import json
import sys
from urllib.parse import urljoin

def test_mobile_oauth():
    """Test mobile OAuth functionality"""
    
    # Configuration
    base_url = "https://optionsplunge.com"  # Change to your domain
    login_url = urljoin(base_url, "/login")
    google_login_url = urljoin(base_url, "/login/google")
    debug_url = urljoin(base_url, "/debug/google-oauth")
    
    print("🧪 Testing Mobile OAuth Functionality")
    print("=" * 50)
    
    # Test 1: Check OAuth configuration
    print("\n1. Testing OAuth Configuration...")
    try:
        response = requests.get(debug_url, timeout=10)
        if response.status_code == 200:
            config = response.json()
            print("✅ OAuth Configuration:")
            for key, value in config.items():
                print(f"   {key}: {value}")
        else:
            print(f"❌ Failed to get OAuth config: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing OAuth config: {e}")
    
    # Test 2: Test login page accessibility
    print("\n2. Testing Login Page...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
        }
        response = requests.get(login_url, headers=headers, timeout=10)
        if response.status_code == 200:
            print("✅ Login page accessible")
            if 'google' in response.text.lower():
                print("✅ Google OAuth button found on login page")
            else:
                print("⚠️  Google OAuth button not found on login page")
        else:
            print(f"❌ Login page not accessible: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing login page: {e}")
    
    # Test 3: Test Google OAuth redirect
    print("\n3. Testing Google OAuth Redirect...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
            'X-Viewport-Width': '375'  # Simulate mobile viewport
        }
        response = requests.get(google_login_url, headers=headers, timeout=10, allow_redirects=False)
        if response.status_code in [302, 301]:
            print("✅ Google OAuth redirect working")
            print(f"   Redirect location: {response.headers.get('Location', 'Not found')}")
        else:
            print(f"❌ Google OAuth redirect failed: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing Google OAuth redirect: {e}")
    
    # Test 4: Test mobile viewport handling
    print("\n4. Testing Mobile Viewport Handling...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
            'X-Viewport-Width': '375'
        }
        response = requests.get(login_url, headers=headers, timeout=10)
        if response.status_code == 200:
            if 'width=device-width' in response.text and 'initial-scale=1.0' in response.text:
                print("✅ Mobile viewport meta tag found")
            else:
                print("⚠️  Mobile viewport meta tag not found")
            
            if 'mobile-menu-btn' in response.text:
                print("✅ Mobile menu button found")
            else:
                print("⚠️  Mobile menu button not found")
        else:
            print(f"❌ Failed to test mobile viewport: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing mobile viewport: {e}")
    
    # Test 5: Test dashboard with mobile parameter
    print("\n5. Testing Dashboard Mobile Parameter...")
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1'
        }
        dashboard_url = urljoin(base_url, "/dashboard?mobile=1&force_mobile=1")
        response = requests.get(dashboard_url, headers=headers, timeout=10)
        if response.status_code == 200:
            print("✅ Dashboard accessible with mobile parameters")
            if 'mobile_preference' in response.text or 'mobile-menu-btn' in response.text:
                print("✅ Mobile layout elements found")
            else:
                print("⚠️  Mobile layout elements not found")
        else:
            print(f"❌ Dashboard not accessible: {response.status_code}")
    except Exception as e:
        print(f"❌ Error testing dashboard: {e}")
    
    print("\n" + "=" * 50)
    print("🎯 Mobile OAuth Test Summary")
    print("=" * 50)
    print("If all tests pass, your mobile OAuth should work correctly.")
    print("If any tests fail, check the specific error messages above.")
    print("\nCommon issues and solutions:")
    print("1. OAuth not configured: Set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET")
    print("2. Mobile viewport issues: Check the viewport meta tag in base.html")
    print("3. Redirect issues: Verify Google OAuth redirect URIs in Google Console")
    print("4. Mobile layout issues: Check CSS media queries and JavaScript")

def test_local_oauth():
    """Test OAuth on local development server"""
    print("\n🔧 Testing Local OAuth Configuration...")
    
    try:
        # Check environment variables
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        
        client_id = os.getenv('GOOGLE_OAUTH_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET')
        
        print(f"Google OAuth Client ID: {'✅ Set' if client_id else '❌ Not set'}")
        print(f"Google OAuth Client Secret: {'✅ Set' if client_secret else '❌ Not set'}")
        
        if client_id and client_secret:
            print("✅ OAuth environment variables are configured")
        else:
            print("❌ OAuth environment variables are missing")
            print("   Please set GOOGLE_OAUTH_CLIENT_ID and GOOGLE_OAUTH_CLIENT_SECRET in your .env file")
            
    except ImportError:
        print("❌ python-dotenv not installed. Install with: pip install python-dotenv")
    except Exception as e:
        print(f"❌ Error checking local OAuth config: {e}")

if __name__ == "__main__":
    print("Mobile OAuth Testing Tool")
    print("=" * 50)
    
    if len(sys.argv) > 1 and sys.argv[1] == "--local":
        test_local_oauth()
    else:
        test_mobile_oauth()
        test_local_oauth()
    
    print("\n📱 To test on actual mobile device:")
    print("1. Visit https://optionsplunge.com/login on your mobile device")
    print("2. Click 'Sign in with Google'")
    print("3. Complete the OAuth flow")
    print("4. Verify you're redirected to the dashboard with proper mobile layout")
