#!/usr/bin/env python3
"""
Test script to check dark mode functionality when authenticated
"""

import requests
from bs4 import BeautifulSoup
import re

def test_dark_mode_authenticated():
    """Test dark mode functionality when user is authenticated"""
    
    base_url = "http://localhost:5000"
    
    print("Testing dark mode functionality (authenticated)...")
    print("=" * 60)
    
    # Create a session to maintain login state
    session = requests.Session()
    
    try:
        # First, try to log in
        print("1. Attempting to log in...")
        
        # Get the login page to get CSRF token
        login_response = session.get(f"{base_url}/login")
        if login_response.status_code != 200:
            print(f"✗ Could not access login page: {login_response.status_code}")
            return
            
        login_soup = BeautifulSoup(login_response.text, 'html.parser')
        csrf_token = login_soup.find('input', {'name': 'csrf_token'})
        
        if not csrf_token:
            print("✗ CSRF token not found on login page")
            return
            
        csrf_value = csrf_token.get('value')
        print(f"✓ CSRF token found: {csrf_value[:10]}...")
        
        # Try to log in with test credentials
        login_data = {
            'csrf_token': csrf_value,
            'username': 'test',  # Assuming this user exists
            'password': 'test123'  # Assuming this password works
        }
        
        login_post = session.post(f"{base_url}/login", data=login_data, allow_redirects=False)
        
        if login_post.status_code == 302:
            print("✓ Login successful (redirected)")
        else:
            print(f"✗ Login failed: {login_post.status_code}")
            print("Note: You may need to create a test user or use correct credentials")
            return
            
        # Now try to access the settings page
        print("\n2. Accessing settings page...")
        settings_response = session.get(f"{base_url}/settings")
        
        if settings_response.status_code == 200:
            print("✓ Settings page accessed successfully")
            
            settings_soup = BeautifulSoup(settings_response.text, 'html.parser')
            
            # Look for the form
            form = settings_soup.find('form')
            if form:
                print("✓ Settings form found")
                
                # Look for all input fields
                inputs = form.find_all('input')
                print(f"\nFound {len(inputs)} input fields:")
                for inp in inputs:
                    input_type = inp.get('type', 'text')
                    input_name = inp.get('name', 'no-name')
                    input_id = inp.get('id', 'no-id')
                    input_checked = inp.get('checked', False)
                    print(f"  - {input_name} (type: {input_type}, id: {input_id}, checked: {input_checked})")
                    
                # Look specifically for dark_mode
                dark_mode_input = form.find('input', {'name': 'dark_mode'})
                if dark_mode_input:
                    print(f"\n✓ Dark mode input found:")
                    print(f"  Type: {dark_mode_input.get('type')}")
                    print(f"  Name: {dark_mode_input.get('name')}")
                    print(f"  ID: {dark_mode_input.get('id')}")
                    print(f"  Checked: {dark_mode_input.get('checked')}")
                    print(f"  HTML: {dark_mode_input}")
                else:
                    print("\n✗ Dark mode input not found")
                    
                # Look for dark mode label
                dark_mode_label = settings_soup.find('label', string=lambda text: text and 'dark mode' in text.lower())
                if dark_mode_label:
                    print(f"\n✓ Dark mode label found:")
                    print(f"  Text: {dark_mode_label.get_text().strip()}")
                    print(f"  For: {dark_mode_label.get('for')}")
                else:
                    print("\n✗ Dark mode label not found")
                    
            else:
                print("✗ Settings form not found")
                
        else:
            print(f"✗ Could not access settings page: {settings_response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Request error: {e}")
    
    print("=" * 60)

if __name__ == "__main__":
    print("Make sure the Flask app is running on http://localhost:5000")
    print("Note: This test assumes a user 'test' with password 'test123' exists")
    print("Press Enter to start testing...")
    input()
    test_dark_mode_authenticated()
