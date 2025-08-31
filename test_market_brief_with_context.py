#!/usr/bin/env python3
"""
Test script to run a manual market brief with proper Flask context
"""

import os
import sys

# Add the current directory to Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_market_brief_with_context():
    """Test market brief generation with proper Flask context"""
    try:
        print("🔍 Testing Market Brief Generation with Flask Context...")
        print("=" * 60)
        
        # Import Flask app
        from app import app
        
        print("✅ Flask app imported successfully")
        
        # Run within application context
        with app.app_context():
            print("✅ Flask application context established")
            
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
                market_brief_files = [f for f in files if "brief" in f.lower()]
                print(f"\n📁 Found {len(market_brief_files)} market brief files in uploads:")
                for file in market_brief_files:
                    file_path = os.path.join(uploads_dir, file)
                    file_size = os.path.getsize(file_path)
                    print(f"   - {file} ({file_size} bytes)")
                    
                    # Show first few lines of the latest brief
                    if "latest" in file.lower():
                        print(f"\n📄 Preview of {file}:")
                        try:
                            with open(file_path, 'r', encoding='utf-8') as f:
                                content = f.read()
                                preview = content[:500] + "..." if len(content) > 500 else content
                                print(preview)
                        except Exception as e:
                            print(f"   Error reading file: {e}")
        
        return True
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"❌ Error running market brief: {e}")
        return False

if __name__ == "__main__":
    success = test_market_brief_with_context()
    if success:
        print("\n🎉 Market brief test completed successfully!")
        print("\n🌐 You can now check the market brief page at:")
        print("   https://optionsplunge.com/market-brief")
    else:
        print("\n❌ Market brief test failed!")
        sys.exit(1)

