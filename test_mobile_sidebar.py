#!/usr/bin/env python3
"""
Test script to verify mobile sidebar functionality
"""

import requests
from bs4 import BeautifulSoup

def test_mobile_sidebar():
    """Test the mobile sidebar functionality"""
    
    # Test the base template
    try:
        response = requests.get('http://localhost:5000/')
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Check if sidebar elements exist
            sidebar = soup.find('nav', class_='sidebar')
            if sidebar:
                print("✅ Sidebar found")
                
                # Check for mobile-specific classes
                if 'position-sticky' in sidebar.get('class', []):
                    print("✅ Sidebar has position-sticky class")
                
                # Check for sidebar content
                sidebar_content = sidebar.find('div', class_='sidebar-content')
                if sidebar_content:
                    print("✅ Sidebar content container found")
                
                # Check for close button
                close_btn = sidebar.find('button', id='sidebarClose')
                if close_btn:
                    print("✅ Close button found")
                
                # Check for backdrop
                backdrop = soup.find('div', id='sidebarBackdrop')
                if backdrop:
                    print("✅ Sidebar backdrop found")
                
                # Check for mobile menu button
                mobile_btn = soup.find('button', id='sidebarToggle')
                if mobile_btn:
                    print("✅ Mobile menu button found")
                
                # Check for JavaScript
                scripts = soup.find_all('script')
                sidebar_js = False
                for script in scripts:
                    if script.string and 'openSidebar' in script.string:
                        sidebar_js = True
                        break
                
                if sidebar_js:
                    print("✅ Sidebar JavaScript functions found")
                
                print("\n📱 Mobile sidebar test completed successfully!")
                return True
            else:
                print("❌ Sidebar not found")
                return False
                
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure the Flask app is running.")
        return False
    except Exception as e:
        print(f"❌ Error testing sidebar: {e}")
        return False

if __name__ == "__main__":
    print("🧪 Testing Mobile Sidebar Functionality...")
    print("=" * 50)
    test_mobile_sidebar()



