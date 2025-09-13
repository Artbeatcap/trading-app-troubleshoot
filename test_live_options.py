#!/usr/bin/env python3
"""
Test script to verify options calculator functionality on live server
"""

import os
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

def main():
    """Run all tests"""
    print("🚀 Testing Options Calculator on Live Server\n")
    
    # Test 1: Token configuration
    if not test_tradier_token():
        print("\n❌ Token configuration failed.")
        return
    
    # Test 2: API connection
    if not test_tradier_api_connection():
        print("\n❌ API connection failed.")
        return
    
    print("\n🎉 All tests passed! The options calculator should now work properly.")
    print("\n📝 Next steps:")
    print("   1. Visit https://optionsplunge.com/tools/options-calculator")
    print("   2. Test with a stock symbol (e.g., AAPL)")
    print("   3. Verify the 500 error is resolved")

if __name__ == "__main__":
    main()



