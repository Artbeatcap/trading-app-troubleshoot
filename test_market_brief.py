#!/usr/bin/env python3
"""
Test script to run a manual market brief
"""

import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_market_brief():
    """Test market brief generation and sending"""
    try:
        print("🔍 Testing Market Brief Generation...")
        print("=" * 50)
        
        # Import the market brief generator
        from market_brief_generator import send_market_brief_to_subscribers
        
        print("✅ Market brief module imported successfully")
        
        # Send the market brief
        print("\n📧 Sending test market brief...")
        result = send_market_brief_to_subscribers()
        
        print(f"✅ Market brief sent to {result} subscribers")
        
        # Check if the brief was saved to static/uploads
        uploads_dir = "static/uploads"
        if os.path.exists(uploads_dir):
            files = os.listdir(uploads_dir)
            market_brief_files = [f for f in files if "market_brief" in f.lower()]
            print(f"\n📁 Found {len(market_brief_files)} market brief files in uploads:")
            for file in market_brief_files:
                print(f"   - {file}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error running market brief: {e}")
        return False

if __name__ == "__main__":
    success = test_market_brief()
    if success:
        print("\n🎉 Market brief test completed successfully!")
    else:
        print("\n❌ Market brief test failed!")
        sys.exit(1)

