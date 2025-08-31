#!/usr/bin/env python3
"""
Simple VPS test script for market brief functionality
"""
import os
import sys
from datetime import datetime

def test_environment():
    """Test environment variables"""
    print("🔧 Testing Environment")
    print("=" * 40)
    
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        required_vars = ['FINNHUB_TOKEN', 'OPENAI_API_KEY', 'DATABASE_URL']
        for var in required_vars:
            value = os.getenv(var)
            if value:
                print(f"✅ {var}: SET (length: {len(value)})")
            else:
                print(f"❌ {var}: NOT SET")
        
        return True
    except Exception as e:
        print(f"❌ Environment test failed: {e}")
        return False

def test_finnhub():
    """Test Finnhub API"""
    print("\n📊 Testing Finnhub API")
    print("=" * 40)
    
    try:
        import requests
        from dotenv import load_dotenv
        load_dotenv()
        
        token = os.getenv('FINNHUB_TOKEN')
        if not token:
            print("❌ FINNHUB_TOKEN not set")
            return False
        
        response = requests.get('https://finnhub.io/api/v1/quote', 
                              params={'symbol': 'AAPL', 'token': token}, 
                              timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Finnhub API working - AAPL: ${data.get('c', 'N/A')}")
            return True
        else:
            print(f"❌ Finnhub API error: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Finnhub API error: {str(e)}")
        return False

def test_market_brief():
    """Test market brief generator"""
    print("\n📰 Testing Market Brief Generator")
    print("=" * 40)
    
    try:
        from market_brief_generator import (
            fetch_news, 
            fetch_stock_prices, 
            calculate_expected_range,
            generate_fallback_summary,
            generate_email_content
        )
        
        # Test news
        headlines = fetch_news()
        print(f"✅ Retrieved {len(headlines)} headlines")
        
        # Test prices
        prices = fetch_stock_prices()
        print(f"✅ Retrieved prices for {len(prices)} symbols")
        
        # Test range calculation
        ranges = calculate_expected_range(prices)
        print(f"✅ Calculated ranges for {len(ranges)} symbols")
        
        # Test summary
        summary = generate_fallback_summary(headlines, ranges)
        print(f"✅ Generated summary ({len(summary)} characters)")
        
        # Test HTML generation
        html_content = generate_email_content(summary, headlines, ranges)
        print(f"✅ Generated HTML ({len(html_content)} characters)")
        
        # Save to file
        from pathlib import Path
        uploads_dir = Path('static/uploads')
        uploads_dir.mkdir(parents=True, exist_ok=True)
        (uploads_dir / 'brief_latest.html').write_text(html_content)
        (uploads_dir / 'brief_latest_date.txt').write_text(datetime.now().strftime('%Y-%m-%d'))
        print("✅ Saved to static/uploads/")
        
        return True
        
    except Exception as e:
        print(f"❌ Market brief test failed: {str(e)}")
        return False

def main():
    """Run all tests"""
    print("🚀 VPS Market Brief Test")
    print("=" * 50)
    print(f"Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Python version: {sys.version}")
    print(f"Current directory: {os.getcwd()}")
    print()
    
    tests = [
        ("Environment", test_environment),
        ("Finnhub API", test_finnhub),
        ("Market Brief Generator", test_market_brief)
    ]
    
    results = {}
    for test_name, test_func in tests:
        try:
            results[test_name] = test_func()
        except Exception as e:
            print(f"❌ {test_name} failed: {str(e)}")
            results[test_name] = False
    
    # Summary
    print("\n" + "=" * 50)
    print("📋 VPS TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(results.values())
    total = len(results)
    
    for test_name, result in results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{test_name}: {status}")
    
    print(f"\nOverall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Market brief system is working on VPS.")
    else:
        print("⚠️ Some tests failed. Check issues above.")
    
    print("=" * 50)

if __name__ == "__main__":
    main()
