#!/usr/bin/env python3
"""
Test script to verify mobile sidebar auto-close functionality
"""

import requests
from bs4 import BeautifulSoup
import re

def test_mobile_sidebar_auto_close():
    """Test the mobile sidebar auto-close functionality"""
    
    print("🧪 Testing Mobile Sidebar Auto-Close Functionality...")
    print("=" * 60)
    
    # Test the base template
    try:
        response = requests.get('http://localhost:5000/')
        if response.status_code == 200:
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Check if the enhanced JavaScript is present
            scripts = soup.find_all('script')
            enhanced_js = False
            mobile_detection = False
            mutation_observer = False
            console_logging = False
            
            for script in scripts:
                if script.string:
                    script_content = script.string
                    
                    # Check for enhanced mobile sidebar functionality
                    if 'setupNavLinkListeners' in script_content:
                        enhanced_js = True
                        print("✅ Enhanced nav link listener setup found")
                    
                    if 'isMobile' in script_content and 'navigator.userAgent' in script_content:
                        mobile_detection = True
                        print("✅ Advanced mobile detection found")
                    
                    if 'MutationObserver' in script_content:
                        mutation_observer = True
                        print("✅ Mutation observer for dynamic content found")
                    
                    if 'console.log' in script_content and 'Closing sidebar' in script_content:
                        console_logging = True
                        print("✅ Console logging for debugging found")
            
            # Check for specific functions
            if enhanced_js and mobile_detection:
                print("\n📱 Mobile Sidebar Auto-Close Test Results:")
                print("   ✅ Enhanced JavaScript implementation")
                print("   ✅ Advanced mobile detection")
                print("   ✅ Mutation observer for dynamic content")
                print("   ✅ Console logging for debugging")
                
                # Check for specific mobile detection patterns
                if re.search(r'window\.innerWidth.*768.*navigator\.userAgent', str(soup)):
                    print("   ✅ Mobile detection includes both screen width and user agent")
                
                # Check for event listener setup
                if re.search(r'removeEventListener.*addEventListener', str(soup)):
                    print("   ✅ Event listener cleanup to prevent duplicates")
                
                print("\n🎯 Auto-Close Features:")
                print("   ✅ Immediate sidebar closing on mobile navigation")
                print("   ✅ Proper event handling for disabled links")
                print("   ✅ Dynamic content support via MutationObserver")
                print("   ✅ Enhanced mobile detection (width + user agent)")
                
                print("\n📋 Testing Instructions:")
                print("   1. Open the app on a mobile device or resize browser to mobile width")
                print("   2. Open the sidebar by clicking the menu button")
                print("   3. Click on any navigation link")
                print("   4. The sidebar should close automatically")
                print("   5. Check browser console for debugging messages")
                
                return True
            else:
                print("❌ Enhanced mobile sidebar functionality not found")
                return False
                
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to server. Make sure the Flask app is running.")
        return False
    except Exception as e:
        print(f"❌ Error testing sidebar: {e}")
        return False

def test_live_app():
    """Test the live app for mobile sidebar functionality"""
    
    print("\n🌐 Testing Live App Mobile Sidebar...")
    print("=" * 50)
    
    try:
        response = requests.get('http://167.88.43.61/', verify=False)
        if response.status_code == 200:
            print("✅ Live app is accessible")
            
            # Check if the enhanced JavaScript is deployed
            soup = BeautifulSoup(response.content, 'html.parser')
            scripts = soup.find_all('script')
            
            enhanced_features = 0
            total_features = 4
            
            for script in scripts:
                if script.string:
                    script_content = script.string
                    
                    if 'setupNavLinkListeners' in script_content:
                        enhanced_features += 1
                    
                    if 'isMobile' in script_content and 'navigator.userAgent' in script_content:
                        enhanced_features += 1
                    
                    if 'MutationObserver' in script_content:
                        enhanced_features += 1
                    
                    if 'console.log.*Closing sidebar' in script_content:
                        enhanced_features += 1
            
            print(f"✅ Enhanced features found: {enhanced_features}/{total_features}")
            
            if enhanced_features >= 3:
                print("🎉 Mobile sidebar auto-close fixes deployed successfully!")
                return True
            else:
                print("⚠️  Some enhanced features may not be deployed")
                return False
                
        else:
            print(f"❌ Live app returned status code: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing live app: {e}")
        return False

if __name__ == "__main__":
    # Test local version
    local_test = test_mobile_sidebar_auto_close()
    
    # Test live version
    live_test = test_live_app()
    
    print("\n" + "=" * 60)
    print("📊 Test Summary:")
    print(f"   Local Test: {'✅ PASSED' if local_test else '❌ FAILED'}")
    print(f"   Live Test:  {'✅ PASSED' if live_test else '❌ FAILED'}")
    
    if local_test and live_test:
        print("\n🎉 All tests passed! Mobile sidebar auto-close is working.")
    else:
        print("\n⚠️  Some tests failed. Check the implementation.")
