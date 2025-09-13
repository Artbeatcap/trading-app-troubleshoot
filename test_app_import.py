#!/usr/bin/env python3
"""
Test script to check if the Flask app can be imported
"""

import sys
import os

def test_app_import():
    """Test if the Flask app can be imported"""
    
    try:
        print("Testing Flask app import...")
        from app import app
        print("✅ App imported successfully")
        
        # Test if we can create an app context
        with app.app_context():
            print("✅ App context created successfully")
            
        return True
        
    except Exception as e:
        print(f"❌ Error importing app: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_app_import()
    sys.exit(0 if success else 1)



