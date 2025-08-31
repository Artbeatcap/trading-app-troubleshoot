#!/usr/bin/env python3
"""
Test app routes
"""

import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_app_routes():
    """Test if app routes are properly registered"""
    try:
        print("🔍 Testing App Routes...")
        print("=" * 40)
        
        # Import Flask app
        from app import app
        
        print("✅ Flask app imported successfully")
        
        # Check if latest_brief route is registered
        with app.app_context():
            routes = [rule.rule for rule in app.url_map.iter_rules()]
            
            print(f"\n📋 Found {len(routes)} routes:")
            brief_routes = [route for route in routes if 'brief' in route.lower()]
            
            print("\n📧 Brief-related routes:")
            for route in brief_routes:
                print(f"  ✅ {route}")
            
            # Check specifically for latest_brief route
            if '/brief/latest' in routes:
                print("\n✅ /brief/latest route is registered")
            else:
                print("\n❌ /brief/latest route is NOT registered")
            
            # Test the route function directly
            print("\n🔧 Testing latest_brief function...")
            try:
                from app import latest_brief
                print("✅ latest_brief function imported successfully")
                
                # Test if the file exists
                from pathlib import Path
                brief_file = Path('static/uploads/brief_latest.html')
                if brief_file.exists():
                    print(f"✅ Brief file exists: {brief_file}")
                    print(f"   Size: {brief_file.stat().st_size} bytes")
                else:
                    print(f"❌ Brief file missing: {brief_file}")
                    
            except ImportError as e:
                print(f"❌ Error importing latest_brief: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing app routes: {e}")
        return False

if __name__ == "__main__":
    success = test_app_routes()
    if success:
        print("\n🎉 App routes test completed!")
    else:
        print("\n❌ App routes test failed!")
        sys.exit(1)

