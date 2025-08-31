#!/usr/bin/env python3
"""
Add a test route to the app
"""

import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def add_test_route():
    """Add a simple test route to the app"""
    try:
        print("🔧 Adding test route to app...")
        
        # Import Flask app
        from app import app
        
        # Add a simple test route
        @app.route("/test-route")
        def test_route():
            return "Test route working!", 200
        
        print("✅ Test route added successfully")
        
        # Check if the route is registered
        with app.app_context():
            routes = [rule.rule for rule in app.url_map.iter_rules()]
            if '/test-route' in routes:
                print("✅ Test route is registered")
            else:
                print("❌ Test route is not registered")
        
        return True
        
    except Exception as e:
        print(f"❌ Error adding test route: {e}")
        return False

if __name__ == "__main__":
    success = add_test_route()
    if success:
        print("\n🎉 Test route added successfully!")
    else:
        print("\n❌ Failed to add test route!")
        sys.exit(1)

