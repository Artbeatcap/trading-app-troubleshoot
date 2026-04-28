#!/usr/bin/env python3
"""Check if Google button appears in rendered register page"""

import requests

url = "https://optionsplunge.com/register"
response = requests.get(url, timeout=10)

html = response.text

# Check for Google button
has_google_button = "Sign up with Google" in html or "btn-google" in html
has_google_link = 'google.login' in html or '/login/google' in html

print("=" * 50)
print("Register Page Check")
print("=" * 50)
print(f"Page loaded: {response.status_code == 200}")
print(f"Google button text found: {'Sign up with Google' in html}")
print(f"Google button class found: {'btn-google' in html}")
print(f"Google login link found: {has_google_link}")
print(f"Page length: {len(html)} characters")
print("=" * 50)

if has_google_button or has_google_link:
    print("✅ Google OAuth button IS present on the page")
else:
    print("❌ Google OAuth button is NOT present on the page")
    # Show a snippet around where it should be
    if "Create Your Account" in html:
        idx = html.find("Create Your Account")
        print("\nSnippet around registration form:")
        print(html[max(0, idx-200):idx+1000][:500])


