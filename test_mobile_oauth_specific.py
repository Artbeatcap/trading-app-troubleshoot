#!/usr/bin/env python3
"""
Mobile OAuth Specific Test
This script tests mobile OAuth flow to identify "Access blocked" issues
"""

import requests
import json
from urllib.parse import urlparse, parse_qs

def test_mobile_oauth_flow():
    """Test mobile OAuth flow specifically"""
    print("📱 Testing Mobile OAuth Flow")
    print("=" * 50)
    
    # Test with mobile user agent
    mobile_headers = {
        'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0 Mobile/15E148 Safari/604.1',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Accept-Encoding': 'gzip, deflate',
        'Connection': 'keep-alive',
        'Upgrade-Insecure-Requests': '1'
    }
    
    try:
        # Step 1: Test login page with mobile user agent
        print("1. Testing login page with mobile user agent...")
        response = requests.get("https://optionsplunge.com/login", headers=mobile_headers, timeout=10)
        print(f"   Status: {response.status_code}")
        print(f"   Content-Type: {response.headers.get('Content-Type', 'Not found')}")
        
        # Step 2: Test OAuth redirect with mobile user agent
        print("\n2. Testing OAuth redirect with mobile user agent...")
        response = requests.get("https://optionsplunge.com/login/google", 
                              headers=mobile_headers, 
                              allow_redirects=False, 
                              timeout=10)
        
        if response.status_code in [302, 301]:
            redirect_url = response.headers.get('Location', '')
            print(f"   Redirect Status: {response.status_code}")
            print(f"   Redirect URL: {redirect_url}")
            
            # Parse the redirect URL
            if 'accounts.google.com' in redirect_url:
                parsed_url = urlparse(redirect_url)
                query_params = parse_qs(parsed_url.query)
                
                print(f"   Client ID: {query_params.get('client_id', ['Not found'])[0]}")
                print(f"   Redirect URI: {query_params.get('redirect_uri', ['Not found'])[0]}")
                print(f"   Scope: {query_params.get('scope', ['Not found'])[0]}")
                print(f"   Response Type: {query_params.get('response_type', ['Not found'])[0]}")
                
                # Check for potential issues
                redirect_uri = query_params.get('redirect_uri', [''])[0]
                if redirect_uri != 'https://optionsplunge.com/login/google/authorized':
                    print(f"   ⚠️  Redirect URI mismatch!")
                    print(f"      Expected: https://optionsplunge.com/login/google/authorized")
                    print(f"      Actual: {redirect_uri}")
                else:
                    print(f"   ✅ Redirect URI matches expected format")
            else:
                print(f"   ⚠️  Unexpected redirect URL (not to Google)")
        else:
            print(f"   ❌ OAuth redirect failed: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            
    except Exception as e:
        print(f"   ❌ Error testing mobile OAuth: {e}")

def test_oauth_consent_screen():
    """Test OAuth consent screen configuration"""
    print("\n🔍 Testing OAuth Consent Screen Configuration")
    print("=" * 50)
    
    print("To check OAuth consent screen:")
    print("1. Go to: https://console.cloud.google.com/")
    print("2. Navigate to: APIs & Services > OAuth consent screen")
    print("3. Check the following:")
    print("   - App name: Should be set")
    print("   - User support email: Should be set")
    print("   - Developer contact information: Should be set")
    print("   - App domain: Should include optionsplunge.com")
    print("   - Authorized domains: Should include optionsplunge.com")
    print("   - Scopes: Should include the required scopes")
    print("   - Test users: If in testing mode, add your email")

def test_mobile_specific_issues():
    """Test mobile-specific OAuth issues"""
    print("\n📱 Mobile-Specific OAuth Issues")
    print("=" * 50)
    
    print("Common mobile OAuth issues:")
    print("1. **User-Agent Detection**: Google may treat mobile differently")
    print("2. **HTTPS Requirements**: Mobile browsers are stricter about HTTPS")
    print("3. **App Verification**: Unverified apps show warnings on mobile")
    print("4. **Test Users**: If app is in testing, mobile users need to be added")
    print("5. **OAuth Consent Screen**: Mobile shows different consent screen")
    
    print("\nSolutions to try:")
    print("1. **Add test users** to OAuth consent screen if in testing mode")
    print("2. **Verify your app** with Google (for production)")
    print("3. **Check OAuth consent screen** configuration")
    print("4. **Ensure HTTPS** is properly configured")
    print("5. **Clear mobile browser cache** and cookies")

def generate_mobile_oauth_fix_guide():
    """Generate mobile OAuth fix guide"""
    print("\n📋 Mobile OAuth Fix Guide")
    print("=" * 50)
    
    print("""
To fix "Access blocked, this app's request invalid" on mobile:

STEP 1: Check OAuth Consent Screen
1. Go to: https://console.cloud.google.com/
2. Navigate to: APIs & Services > OAuth consent screen
3. If app is in "Testing" mode:
   - Add your email address as a test user
   - Add any other users who need access
4. If app is in "Production" mode:
   - Ensure app is verified by Google
   - Or switch to testing mode temporarily

STEP 2: Verify OAuth Credentials
1. Go to: APIs & Services > Credentials
2. Click on your OAuth 2.0 Client ID
3. Verify Authorized redirect URIs:
   https://optionsplunge.com/login/google/authorized
4. Verify Authorized JavaScript origins:
   https://optionsplunge.com

STEP 3: Check App Domain Configuration
1. In OAuth consent screen, verify:
   - App domain includes: optionsplunge.com
   - Authorized domains includes: optionsplunge.com
   - Privacy policy URL (if required)
   - Terms of service URL (if required)

STEP 4: Test on Mobile
1. Clear mobile browser cache and cookies
2. Try OAuth login again
3. If still blocked, try adding your email as test user

STEP 5: Alternative Solutions
1. Switch app to "Testing" mode temporarily
2. Add all necessary test users
3. Test OAuth flow
4. Once working, consider app verification for production
""")

if __name__ == "__main__":
    print("Mobile OAuth Specific Test Tool")
    print("=" * 50)
    
    test_mobile_oauth_flow()
    test_oauth_consent_screen()
    test_mobile_specific_issues()
    generate_mobile_oauth_fix_guide()
    
    print("\n" + "=" * 50)
    print("🎯 Most likely cause: OAuth consent screen configuration")
    print("   - Add your email as a test user if app is in testing mode")
    print("   - Or verify your app with Google for production use")
