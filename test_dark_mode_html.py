#!/usr/bin/env python3
"""
Test script to check the actual HTML output of the settings page
"""

import requests
from bs4 import BeautifulSoup
import re

def test_settings_html():
    """Test the actual HTML output of the settings page"""
    
    base_url = "http://localhost:5000"
    
    print("Testing settings page HTML output...")
    print("=" * 60)
    
    try:
        # Get the settings page
        response = requests.get(f"{base_url}/settings", timeout=5)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            print("✓ Settings page loaded successfully")
            
            # Look for the form
            form = soup.find('form')
            if form:
                print("✓ Form found")
                print(f"  Method: {form.get('method')}")
                print(f"  Action: {form.get('action')}")
                
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
                dark_mode_label = soup.find('label', string=lambda text: text and 'dark mode' in text.lower())
                if dark_mode_label:
                    print(f"\n✓ Dark mode label found:")
                    print(f"  Text: {dark_mode_label.get_text().strip()}")
                    print(f"  For: {dark_mode_label.get('for')}")
                else:
                    print("\n✗ Dark mode label not found")
                    
            else:
                print("✗ Form not found")
                
            # Check for any JavaScript errors or issues
            scripts = soup.find_all('script')
            print(f"\nFound {len(scripts)} script tags")
            
            # Check for any error messages or alerts
            alerts = soup.find_all(class_=re.compile(r'alert|error|danger'))
            if alerts:
                print(f"\nFound {len(alerts)} alert/error elements:")
                for alert in alerts:
                    print(f"  - {alert.get_text().strip()}")
            else:
                print("\nNo alert/error elements found")
                
        else:
            print(f"✗ Settings page returned status code: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Could not connect to settings page: {e}")
    
    print("=" * 60)

if __name__ == "__main__":
    print("Make sure the Flask app is running on http://localhost:5000")
    print("Press Enter to start testing...")
    input()
    test_settings_html()
