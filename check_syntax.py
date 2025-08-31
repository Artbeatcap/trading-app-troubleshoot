#!/usr/bin/env python3
"""
Check for syntax errors in app.py
"""

import ast
import sys

def check_syntax():
    """Check for syntax errors in app.py"""
    try:
        print("🔍 Checking app.py syntax...")
        
        with open('app.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse the file to check for syntax errors
        ast.parse(content)
        print("✅ No syntax errors found in app.py")
        
        # Try to import the app
        print("\n🔍 Trying to import app...")
        import app
        print("✅ App imported successfully")
        
        # Check if latest_brief route exists
        if hasattr(app, 'latest_brief'):
            print("✅ latest_brief function exists")
        else:
            print("❌ latest_brief function not found")
        
        return True
        
    except SyntaxError as e:
        print(f"❌ Syntax error in app.py: {e}")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = check_syntax()
    if not success:
        sys.exit(1)

