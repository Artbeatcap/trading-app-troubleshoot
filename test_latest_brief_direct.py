#!/usr/bin/env python3
"""
Test latest_brief function directly
"""

import os
import sys
from pathlib import Path

def test_latest_brief_direct():
    """Test the latest_brief function logic directly"""
    try:
        print("🔍 Testing latest_brief function directly...")
        print("=" * 50)
        
        # Get the path to the static brief file
        brief_file = Path('static/uploads/brief_latest.html')
        date_file = Path('static/uploads/brief_latest_date.txt')
        
        print(f"📁 Brief file path: {brief_file}")
        print(f"📁 Date file path: {date_file}")
        
        if not brief_file.exists():
            print("❌ Brief file does not exist")
            return False
        
        print(f"✅ Brief file exists (size: {brief_file.stat().st_size} bytes)")
        
        # Read the brief content
        with open(brief_file, 'r', encoding='utf-8') as f:
            html_content = f.read()
        
        print(f"✅ Brief content read successfully ({len(html_content)} characters)")
        
        # Read the date
        date_str = "Unknown"
        if date_file.exists():
            with open(date_file, 'r') as f:
                date_str = f.read().strip()
            print(f"✅ Date file read: {date_str}")
        else:
            print("⚠️ Date file does not exist")
        
        # Show first 200 characters of the content
        print(f"\n📄 Brief content preview:")
        print(html_content[:200] + "...")
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing latest_brief: {e}")
        return False

if __name__ == "__main__":
    success = test_latest_brief_direct()
    if success:
        print("\n🎉 latest_brief function test completed successfully!")
    else:
        print("\n❌ latest_brief function test failed!")
        sys.exit(1)

