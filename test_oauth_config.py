#!/usr/bin/env python3
"""
Test script to check OAuth configuration
"""

import os
import re

def check_oauth_config():
    """Check if OAuth credentials are properly configured"""
    print("🔍 Checking Google OAuth Configuration...")
    print("=" * 50)
    
    # Check if .env file exists
    if not os.path.exists('.env'):
        print("❌ .env file not found")
        return False
    
    # Read .env file
    with open('.env', 'r') as f:
        env_content = f.read()
    
    # Check for OAuth variables
    client_id_match = re.search(r'GOOGLE_OAUTH_CLIENT_ID=(.+)', env_content)
    client_secret_match = re.search(r'GOOGLE_OAUTH_CLIENT_SECRET=(.+)', env_content)
    
    if not client_id_match or not client_secret_match:
        print("❌ OAuth variables not found in .env file")
        return False
    
    client_id = client_id_match.group(1).strip()
    client_secret = client_secret_match.group(1).strip()
    
    print(f"Client ID: {client_id}")
    print(f"Client Secret: {client_secret[:10]}..." if len(client_secret) > 10 else f"Client Secret: {client_secret}")
    
    # Check if they're placeholder values
    if 'your-google-client-id-here' in client_id or 'your-google-client-secret-here' in client_secret:
        print("❌ OAuth credentials are still placeholder values")
        print("\n🔧 To fix this:")
        print("1. Go to https://console.cloud.google.com/")
        print("2. Create OAuth 2.0 credentials")
        print("3. Update your .env file with real values")
        return False
    
    # Check if they look like real OAuth credentials
    if not client_id.endswith('.apps.googleusercontent.com'):
        print("⚠️  Client ID doesn't look like a valid Google OAuth client ID")
        print("   Should end with: .apps.googleusercontent.com")
        return False
    
    if not client_secret.startswith('GOCSPX-'):
        print("⚠️  Client Secret doesn't look like a valid Google OAuth client secret")
        print("   Should start with: GOCSPX-")
        return False
    
    print("✅ OAuth credentials appear to be properly configured")
    return True

def check_oauth_transport():
    """Check OAuth transport configuration"""
    print("\n🔍 Checking OAuth Transport Configuration...")
    
    with open('.env', 'r') as f:
        env_content = f.read()
    
    transport_match = re.search(r'OAUTHLIB_INSECURE_TRANSPORT=(\d+)', env_content)
    
    if transport_match and transport_match.group(1) == '1':
        print("✅ OAuth insecure transport enabled for development")
        return True
    else:
        print("⚠️  OAuth insecure transport not configured")
        print("   Add: OAUTHLIB_INSECURE_TRANSPORT=1 to .env for development")
        return False

def main():
    print("🚀 Google OAuth Configuration Check")
    print("=" * 50)
    
    oauth_ok = check_oauth_config()
    transport_ok = check_oauth_transport()
    
    print("\n" + "=" * 50)
    print("📋 Summary:")
    
    if oauth_ok and transport_ok:
        print("✅ OAuth configuration looks good!")
        print("🎯 Try logging in at: http://localhost:5000/login")
    else:
        print("❌ OAuth configuration needs attention")
        print("📖 See: GOOGLE_OAUTH_SETUP_GUIDE.md for setup instructions")
    
    print("\n🔧 Next Steps:")
    print("1. Set up Google OAuth credentials")
    print("2. Update .env file with real values")
    print("3. Restart Flask app")
    print("4. Test login at: http://localhost:5000/login")

if __name__ == "__main__":
    main()

