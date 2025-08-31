#!/usr/bin/env python3

import os
from dotenv import load_dotenv

def test_data_availability():
    """Test data availability for market brief"""
    
    print("🧪 Testing Data Availability")
    print("=" * 40)
    
    # Load environment variables
    load_dotenv()
    
    # Import functions
    from market_brief_generator import fetch_news, fetch_stock_prices, generate_market_summary
    
    # Test news
    print("\n📰 Testing News APIs:")
    headlines = fetch_news()
    print(f"Headlines fetched: {len(headlines)}")
    
    # Test stock prices
    print("\n📊 Testing Stock Price APIs:")
    prices = fetch_stock_prices()
    print(f"Prices fetched: {len(prices)}")
    if prices:
        for symbol, data in prices.items():
            print(f"  {symbol}: ${data.get('current_price', 0):.2f}")
    
    # Test market summary generation
    print("\n📝 Testing Market Summary Generation:")
    summary = generate_market_summary(prices, headlines)
    
    if "Market Data Unavailable" in summary:
        print("❌ Market data unavailable")
    elif "Market Headlines Unavailable" in summary:
        print("❌ Market headlines unavailable")
    else:
        print("✅ Market summary generated successfully")
    
    print(f"\nSummary length: {len(summary)} characters")
    print(f"First 100 chars: {summary[:100]}...")

if __name__ == "__main__":
    test_data_availability()
