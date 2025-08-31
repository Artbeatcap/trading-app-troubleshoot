#!/usr/bin/env python3
"""
Test script to check dark mode functionality
"""

import requests
from bs4 import BeautifulSoup

def test_dark_mode_form():
    """Test if dark mode form field is present and working"""
    
    base_url = "http://localhost:5000"
    
    print("Testing dark mode form field...")
    print("=" * 50)
    
    try:
        # Get the settings page
        response = requests.get(f"{base_url}/settings", timeout=5)
        
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for dark mode checkbox
            dark_mode_checkbox = soup.find('input', {'name': 'dark_mode'})
            
            if dark_mode_checkbox:
                print("✓ Dark mode checkbox found")
                print(f"  Type: {dark_mode_checkbox.get('type')}")
                print(f"  Name: {dark_mode_checkbox.get('name')}")
                print(f"  Checked: {dark_mode_checkbox.get('checked')}")
            else:
                print("✗ Dark mode checkbox not found")
                
            # Look for dark mode label
            dark_mode_label = soup.find('label', string=lambda text: text and 'dark mode' in text.lower())
            
            if dark_mode_label:
                print("✓ Dark mode label found")
                print(f"  Text: {dark_mode_label.get_text().strip()}")
            else:
                print("✗ Dark mode label not found")
                
            # Check if form has the correct structure
            form = soup.find('form')
            if form:
                print("✓ Form found")
                print(f"  Method: {form.get('method')}")
                print(f"  Action: {form.get('action')}")
            else:
                print("✗ Form not found")
                
        else:
            print(f"✗ Settings page returned status code: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"✗ Could not connect to settings page: {e}")
    
    print("=" * 50)

if __name__ == "__main__":
    print("Make sure the Flask app is running on http://localhost:5000")
    print("Press Enter to start testing...")
    input()
    test_dark_mode_form()
