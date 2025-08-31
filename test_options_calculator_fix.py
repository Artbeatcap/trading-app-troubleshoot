#!/usr/bin/env python3
"""
Test script to verify options calculator functionality after fixing Tradier API token
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_tradier_token():
    """Test if Tradier API token is properly configured"""
    print("🔍 Testing Tradier API Token Configuration...")
    
    token = os.getenv('TRADIER_API_TOKEN')
    if not token:
        print("❌ TRADIER_API_TOKEN not found in environment variables")
        return False
    
    if token == "your_tradier_token_here" or token == "your-tradier-token":
        print("❌ TRADIER_API_TOKEN is set to placeholder value")
        return False
    
    print(f"✅ TRADIER_API_TOKEN is configured: {token[:10]}...")
    return True

def test_tradier_api_connection():
    """Test basic Tradier API connectivity"""
    print("\n🔍 Testing Tradier API Connection...")
    
    try:
        import requests
        
        token = os.getenv('TRADIER_API_TOKEN')
        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
        
        # Test with a simple quote request
        url = "https://api.tradier.com/v1/markets/quotes"
        params = {"symbols": "AAPL"}
        
        print("Making test request to Tradier API...")
        response = requests.get(url, params=params, headers=headers, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Tradier API connection successful")
            print(f"   Response status: {response.status_code}")
            return True
        else:
            print(f"❌ Tradier API error: {response.status_code}")
            print(f"   Response: {response.text[:200]}...")
            return False
            
    except Exception as e:
        print(f"❌ Error testing Tradier API: {e}")
        return False

def test_options_calculator_functions():
    """Test the options calculator functions directly"""
    print("\n🔍 Testing Options Calculator Functions...")
    
    try:
        # Import the functions from app.py
        sys.path.append('.')
        from app import get_stock_price_tradier, get_expiration_dates_tradier, get_options_chain_tradier
        
        # Test stock price function
        print("Testing get_stock_price_tradier...")
        price, description = get_stock_price_tradier("AAPL")
        if price:
            print(f"✅ Stock price retrieved: ${price} for {description}")
        else:
            print("❌ Failed to get stock price")
            return False
        
        # Test expiration dates function
        print("Testing get_expiration_dates_tradier...")
        expirations = get_expiration_dates_tradier("AAPL")
        if expirations:
            print(f"✅ Expiration dates retrieved: {len(expirations)} dates")
            print(f"   First few dates: {expirations[:3]}")
        else:
            print("❌ Failed to get expiration dates")
            return False
        
        # Test options chain function (with first expiration date)
        if expirations:
            print("Testing get_options_chain_tradier...")
            calls, puts, current_price, _ = get_options_chain_tradier("AAPL", expirations[0])
            if calls is not None and puts is not None:
                print(f"✅ Options chain retrieved successfully")
                print(f"   Calls: {len(calls)} contracts")
                print(f"   Puts: {len(puts)} contracts")
                print(f"   Current price: ${current_price}")
                return True
            else:
                print("❌ Failed to get options chain")
                return False
        
        return True
        
    except Exception as e:
        print(f"❌ Error testing options calculator functions: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Run all tests"""
    print("🚀 Testing Options Calculator Fix\n")
    
    # Test 1: Token configuration
    if not test_tradier_token():
        print("\n❌ Token configuration failed. Please check your .env file.")
        return
    
    # Test 2: API connection
    if not test_tradier_api_connection():
        print("\n❌ API connection failed. Please check your internet connection and API token.")
        return
    
    # Test 3: Options calculator functions
    if not test_options_calculator_functions():
        print("\n❌ Options calculator functions failed.")
        return
    
    print("\n🎉 All tests passed! The options calculator should now work properly.")
    print("\n📝 Next steps:")
    print("   1. Restart your Flask application")
    print("   2. Visit /tools/options-calculator in your browser")
    print("   3. Try searching for a stock symbol (e.g., AAPL)")

if __name__ == "__main__":
    main()
