#!/usr/bin/env python3
"""
OAuth Redirect URI Fix Script
This script helps diagnose and fix the redirect_uri_mismatch error
"""

import requests
import json
import sys
from urllib.parse import urljoin, urlparse

def check_oauth_configuration():
    """Check the current OAuth configuration"""
    print("🔍 Checking OAuth Configuration...")
    print("=" * 50)
    
    # Check local environment
    try:
        import os
        from dotenv import load_dotenv
        
        load_dotenv()
        
        client_id = os.getenv('GOOGLE_OAUTH_CLIENT_ID')
        client_secret = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET')
        
        print(f"Google OAuth Client ID: {'✅ Set' if client_id else '❌ Not set'}")
        print(f"Google OAuth Client Secret: {'✅ Set' if client_secret else '❌ Not set'}")
        
        if client_id:
            print(f"Client ID: {client_id[:20]}...{client_id[-10:]}")
        
    except ImportError:
        print("❌ python-dotenv not installed")
    except Exception as e:
        print(f"❌ Error checking local config: {e}")

def check_live_oauth_config():
    """Check the live OAuth configuration"""
    print("\n🌐 Checking Live OAuth Configuration...")
    print("=" * 50)
    
    try:
        # Test the live OAuth debug endpoint
        response = requests.get("https://optionsplunge.com/debug/google-oauth", timeout=10)
        if response.status_code == 200:
            config = response.json()
            print("✅ Live OAuth debug endpoint accessible")
            print(f"Expected Redirect URI: {config.get('expected_redirect_uri', 'Not found')}")
            print(f"Google Authorized: {config.get('google_authorized', 'Unknown')}")
            print(f"Session Config: {config.get('session_config', {})}")
        else:
            print(f"❌ Live OAuth debug endpoint returned: {response.status_code}")
    except Exception as e:
        print(f"❌ Error checking live config: {e}")

def test_oauth_redirect():
    """Test the OAuth redirect flow"""
    print("\n🧪 Testing OAuth Redirect Flow...")
    print("=" * 50)
    
    try:
        # Test the Google login endpoint
        response = requests.get("https://optionsplunge.com/login/google", 
                              allow_redirects=False, 
                              timeout=10)
        
        if response.status_code in [302, 301]:
            redirect_url = response.headers.get('Location', '')
            print(f"✅ OAuth redirect working")
            print(f"Redirect URL: {redirect_url}")
            
            # Parse the redirect URL to extract the redirect_uri parameter
            if 'redirect_uri=' in redirect_url:
                parsed_url = urlparse(redirect_url)
                query_params = dict(parse_qsl(parsed_url.query))
                redirect_uri = query_params.get('redirect_uri', '')
                print(f"Actual Redirect URI: {redirect_uri}")
                
                # Check if it matches the expected format
                expected_uri = "https://optionsplunge.com/login/google/authorized"
                if redirect_uri == expected_uri:
                    print("✅ Redirect URI matches expected format")
                else:
                    print("❌ Redirect URI mismatch!")
                    print(f"Expected: {expected_uri}")
                    print(f"Actual: {redirect_uri}")
            else:
                print("⚠️  No redirect_uri parameter found in redirect URL")
        else:
            print(f"❌ OAuth redirect failed: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            
    except Exception as e:
        print(f"❌ Error testing OAuth redirect: {e}")

def generate_oauth_setup_instructions():
    """Generate OAuth setup instructions"""
    print("\n📋 Google OAuth Console Setup Instructions")
    print("=" * 50)
    
    print("""
To fix the redirect_uri_mismatch error, you need to update your Google OAuth configuration:

1. Go to Google Cloud Console: https://console.cloud.google.com/
2. Select your project
3. Go to "APIs & Services" > "Credentials"
4. Find your OAuth 2.0 Client ID and click on it
5. In the "Authorized redirect URIs" section, add these URLs:

   ✅ REQUIRED (Production):
   https://optionsplunge.com/login/google/authorized

   ✅ OPTIONAL (Development/Testing):
   http://localhost:5000/login/google/authorized
   http://127.0.0.1:5000/login/google/authorized

6. Click "Save"

IMPORTANT NOTES:
- Make sure there are no trailing slashes
- The domain must match exactly (https://optionsplunge.com)
- The path must be exactly: /login/google/authorized
- Remove any old/incorrect redirect URIs

After updating the Google Console:
1. Wait 5-10 minutes for changes to propagate
2. Clear your browser cache and cookies
3. Test the OAuth login again
""")

def check_current_redirect_uris():
    """Check what redirect URIs are currently configured"""
    print("\n🔍 Current Redirect URI Analysis")
    print("=" * 50)
    
    print("Based on your app configuration, the expected redirect URI is:")
    print("https://optionsplunge.com/login/google/authorized")
    print()
    print("Common issues to check:")
    print("1. Missing 'https://' protocol")
    print("2. Wrong domain (should be optionsplunge.com)")
    print("3. Wrong path (should be /login/google/authorized)")
    print("4. Extra trailing slash")
    print("5. Missing the 'authorized' part of the path")
    print()
    print("Your Google OAuth console should have EXACTLY:")
    print("https://optionsplunge.com/login/google/authorized")

def parse_qsl(query_string):
    """Parse query string to dictionary"""
    from urllib.parse import parse_qs
    return [(k, v[0] if v else '') for k, v in parse_qs(query_string).items()]

if __name__ == "__main__":
    print("OAuth Redirect URI Fix Tool")
    print("=" * 50)
    
    check_oauth_configuration()
    check_live_oauth_config()
    test_oauth_redirect()
    check_current_redirect_uris()
    generate_oauth_setup_instructions()
    
    print("\n" + "=" * 50)
    print("🎯 Next Steps:")
    print("1. Update your Google OAuth console with the correct redirect URI")
    print("2. Wait 5-10 minutes for changes to propagate")
    print("3. Clear browser cache and test again")
    print("4. If issues persist, check the Google OAuth console logs")
