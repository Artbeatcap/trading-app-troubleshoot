#!/usr/bin/env python3
"""
Test script for Tradier integration
Tests minute bars, quotes, and gap calculations
"""

import asyncio
import pytz
import datetime as dt
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

async def test_tradier_basic():
    """Test basic Tradier functionality"""
    try:
        from tradier_provider import TradierProvider
        
        print("✅ TradierProvider imported successfully")
        
        # Test provider initialization
        provider = TradierProvider()
        print("✅ TradierProvider initialized")
        
        # Test timezone setup
        tz = pytz.timezone("America/New_York")
        now = dt.datetime.now(tz)
        print(f"✅ Timezone setup: {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
        
        # Test symbols
        test_symbols = ["AAPL", "NVDA", "TSLA", "AMD", "AMZN"]
        print(f"✅ Test symbols: {test_symbols}")
        
        return provider, tz, test_symbols
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        return None, None, None
    except Exception as e:
        print(f"❌ Setup error: {e}")
        return None, None, None

async def test_minute_bars(provider, tz, symbols):
    """Test minute bars fetching"""
    if not provider:
        return
    
    try:
        # Set up time window (7:00 AM to 9:24 AM ET today)
        now = dt.datetime.now(tz)
        start = int(tz.localize(dt.datetime(now.year, now.month, now.day, 7, 0)).timestamp())
        end = int(tz.localize(dt.datetime(now.year, now.month, now.day, 9, 24)).timestamp())
        
        print(f"📊 Testing minute bars: {dt.datetime.fromtimestamp(start, tz).strftime('%H:%M')} - {dt.datetime.fromtimestamp(end, tz).strftime('%H:%M')}")
        
        # Fetch minute bars
        minutes = await provider.minute_window(symbols, start, end, prepost=True)
        
        print(f"✅ Minute bars fetched for {len([s for s in symbols if minutes.get(s)])} symbols")
        
        # Show sample data
        for sym in symbols[:3]:  # Show first 3
            bars = minutes.get(sym, [])
            if bars:
                print(f"  {sym}: {len(bars)} bars, last: ${bars[-1]['c']:.2f}, vol: {sum(b['v'] for b in bars):,}")
            else:
                print(f"  {sym}: No data")
        
        return minutes
        
    except Exception as e:
        print(f"❌ Minute bars error: {e}")
        return None

async def test_quotes(provider, symbols):
    """Test quotes fetching"""
    if not provider:
        return
    
    try:
        print("📈 Testing quotes fetching...")
        
        # Fetch previous close prices
        prev = await provider.prev_close(symbols)
        
        print(f"✅ Quotes fetched for {len(prev)} symbols")
        
        # Show sample data
        for sym in symbols[:3]:
            pc = prev.get(sym)
            if pc:
                print(f"  {sym}: prev close ${pc:.2f}")
            else:
                print(f"  {sym}: No prev close data")
        
        return prev
        
    except Exception as e:
        print(f"❌ Quotes error: {e}")
        return None

async def test_gap_calculations(minutes, prev):
    """Test gap calculations"""
    if not minutes or not prev:
        return
    
    print("🧮 Testing gap calculations...")
    
    def pct(a, b):
        try:
            return round((a - b) / b * 100, 2)
        except:
            return None
    
    for sym in list(minutes.keys())[:3]:
        bars = minutes.get(sym, [])
        pc = prev.get(sym)
        
        if bars and pc:
            last = bars[-1]["c"]
            gap = pct(last, pc)
            vol = sum(b["v"] for b in bars)
            print(f"  {sym}: ${pc:.2f} → ${last:.2f} = {gap:+.2f}% (vol: {vol:,})")
        else:
            print(f"  {sym}: Insufficient data")

async def test_news(provider):
    """Test news fetching"""
    if not provider:
        return
    
    try:
        print("📰 Testing news fetching...")
        
        # Test news for a major stock
        news = await provider.news("AAPL", since_hours=24)
        
        if news:
            print(f"✅ News fetched: {len(news)} articles")
            if news:
                headline = news[0].get("headline", "")[:100]
                print(f"  Sample: {headline}...")
        else:
            print("⚠️ No news data (this is normal if no recent news)")
        
    except Exception as e:
        print(f"❌ News error: {e}")

async def main():
    """Main test function"""
    print("🚀 Starting Tradier Integration Test")
    print("=" * 50)
    
    # Check environment
    tradier_token = os.getenv("TRADIER_API_TOKEN")
    if not tradier_token:
        print("❌ TRADIER_API_TOKEN not found in environment")
        return
    
    print(f"✅ TRADIER_API_TOKEN found: {tradier_token[:10]}...")
    
    # Test basic setup
    provider, tz, symbols = await test_tradier_basic()
    if not provider:
        return
    
    print("\n" + "=" * 50)
    
    # Test minute bars
    minutes = await test_minute_bars(provider, tz, symbols)
    
    print("\n" + "=" * 50)
    
    # Test quotes
    prev = await test_quotes(provider, symbols)
    
    print("\n" + "=" * 50)
    
    # Test gap calculations
    await test_gap_calculations(minutes, prev)
    
    print("\n" + "=" * 50)
    
    # Test news
    await test_news(provider)
    
    print("\n" + "=" * 50)
    print("✅ Tradier integration test completed!")

if __name__ == "__main__":
    asyncio.run(main())
