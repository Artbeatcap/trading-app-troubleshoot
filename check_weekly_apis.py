#!/usr/bin/env python3
"""Check API keys and test weekly brief data fetching"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from market_brief_generator import fetch_top_movers_av, fetch_economic_calendar_range, fetch_stock_prices

def main():
    print("=== API KEY STATUS ===")
    print(f"ALPHA_VANTAGE_API_KEY: {bool(os.getenv('ALPHA_VANTAGE_API_KEY'))}")
    print(f"FINNHUB_TOKEN: {bool(os.getenv('FINNHUB_TOKEN'))}")
    print(f"TRADIER_API_TOKEN: {bool(os.getenv('TRADIER_API_TOKEN'))}")
    
    print("\n=== TESTING DATA FETCHING ===")
    
    # Test movers
    print("Testing top movers...")
    movers = fetch_top_movers_av()
    print(f"Movers count: {len(movers)}")
    if movers:
        print(f"Sample mover: {movers[0]}")
    
    # Test economic calendar
    print("\nTesting economic calendar...")
    calendar = fetch_economic_calendar_range(days_ahead=7)
    print(f"Calendar events count: {len(calendar)}")
    if calendar:
        print(f"Sample event: {calendar[0]}")
    
    # Test stock prices for levels
    print("\nTesting stock prices...")
    prices = fetch_stock_prices()
    print(f"Price data: {prices}")

if __name__ == "__main__":
    main()
