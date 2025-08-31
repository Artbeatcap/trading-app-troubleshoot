#!/usr/bin/env python3
"""
Debug script to check sidebar rendering
"""

import requests
from bs4 import BeautifulSoup

def debug_sidebar():
    """Debug sidebar rendering issues"""
    
    print("🔍 Debugging Sidebar Rendering...")
    print("=" * 40)
    
    # Test on dashboard page which should show sidebar
    urls_to_test = [
        'http://167.88.43.61/dashboard',
        'http://167.88.43.61/trades',
        'http://167.88.43.61/'
    ]
    
    for url in urls_to_test:
        print(f"\n🌐 Testing: {url}")
        try:
            response = requests.get(url, verify=False)
            print(f"Response status: {response.status_code}")
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Check for sidebar
            sidebar = soup.find('nav', class_='sidebar')
            if sidebar:
                print("✅ Sidebar found")
                print(f"Sidebar classes: {sidebar.get('class', [])}")
                
                # Check if sidebar has 'show' class
                if 'show' in sidebar.get('class', []):
                    print("⚠️  Sidebar has 'show' class by default")
                else:
                    print("✅ Sidebar is hidden by default (no 'show' class)")
                
                # Check for mobile menu button
                mobile_btn = soup.find('button', id='sidebarToggle')
                if mobile_btn:
                    print("✅ Mobile menu button found")
                else:
                    print("❌ Mobile menu button not found")
                
                # Check for JavaScript
                scripts = soup.find_all('script')
                js_found = False
                for script in scripts:
                    if script.string and 'ensureSidebarHidden' in script.string:
                        js_found = True
                        break
                
                if js_found:
                    print("✅ JavaScript sidebar functions found")
                else:
                    print("❌ JavaScript sidebar functions not found")
                
                return  # Found a page with sidebar, no need to test others
                
            else:
                print("❌ Sidebar not found (likely hide_sidebar=True)")
                
        except Exception as e:
            print(f"❌ Error testing {url}: {e}")

if __name__ == "__main__":
    debug_sidebar()
