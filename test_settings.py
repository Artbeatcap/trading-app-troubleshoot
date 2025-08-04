#!/usr/bin/env python3
"""
Test script to verify the enhanced settings functionality
"""

import requests
import time

def test_settings_functionality():
    """Test the settings page functionality"""
    
    base_url = "http://localhost:5000"
    
    print("Testing enhanced settings functionality...")
    print("=" * 60)
    
    # Test 1: Settings page accessibility (should redirect to login if not authenticated)
    print("1. Testing settings page accessibility...")
    try:
        response = requests.get(f"{base_url}/settings", timeout=5, allow_redirects=False)
        if response.status_code == 302:  # Redirect to login
            print("   ✓ Settings page correctly redirects to login when not authenticated")
        else:
            print(f"   ✗ Settings page returned unexpected status: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"   ✗ Could not connect to settings page: {e}")
    
    # Test 2: Settings page content (if we can access it)
    print("2. Testing settings page content...")
    try:
        response = requests.get(f"{base_url}/settings", timeout=5)
        if response.status_code == 200:
            content = response.text.lower()
            
            # Check for new form fields
            expected_fields = [
                'display_name',
                'dark_mode',
                'daily_brief_email',
                'timezone',
                'api_key',
                'account_size',
                'default_risk_percent',
                'auto_analyze_trades',
                'analysis_detail_level',
                'max_daily_loss',
                'max_position_size',
                'trades_per_page'
            ]
            
            missing_fields = []
            for field in expected_fields:
                if field not in content:
                    missing_fields.append(field)
            
            if not missing_fields:
                print("   ✓ All expected settings fields are present")
            else:
                print(f"   ✗ Missing fields: {missing_fields}")
                
            # Check for section headers
            expected_sections = [
                'account & display',
                'trading account',
                'ai analysis preferences',
                'risk management',
                'display preferences',
                'notifications',
                'api settings'
            ]
            
            missing_sections = []
            for section in expected_sections:
                if section not in content:
                    missing_sections.append(section)
            
            if not missing_sections:
                print("   ✓ All expected sections are present")
            else:
                print(f"   ✗ Missing sections: {missing_sections}")
                
        else:
            print(f"   ✗ Settings page returned status code: {response.status_code}")
    except requests.exceptions.RequestException as e:
        print(f"   ✗ Could not access settings page: {e}")
    
    # Test 3: Form submission (this would require authentication)
    print("3. Testing form submission...")
    print("   ℹ Form submission test requires authentication - manual testing needed")
    
    print("=" * 60)
    print("Test completed!")
    print("\nManual testing checklist:")
    print("1. Log in as a test user")
    print("2. Navigate to Settings page")
    print("3. Verify all form fields are pre-filled with current values")
    print("4. Toggle dark-mode and email-brief checkboxes")
    print("5. Change display name and timezone")
    print("6. Save changes and verify flash message appears")
    print("7. Reload page and verify saved values persist")
    print("8. Test that settings are only accessible to authenticated users")

if __name__ == "__main__":
    print("Make sure the Flask app is running on http://localhost:5000")
    print("Press Enter to start testing...")
    input()
    test_settings_functionality() 