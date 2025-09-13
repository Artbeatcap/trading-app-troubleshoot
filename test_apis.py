#!/usr/bin/env python3

import os
import requests
from dotenv import load_dotenv

def test_apis():
    """Test all API tokens"""
    
    print("🔍 Testing API Tokens")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Test Finnhub
    print("\n1. Testing Finnhub:")
    finnhub_token = os.getenv('FINNHUB_TOKEN')
    if finnhub_token:
        print(f"✅ Token found: {finnhub_token[:20]}...")
        try:
            test_url = "https://finnhub.io/api/v1/quote"
            test_params = {'symbol': 'AAPL', 'token': finnhub_token}
            response = requests.get(test_url, params=test_params, timeout=10)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print("✅ Finnhub API working!")
            else:
                print(f"❌ Finnhub API failed: {response.text[:100]}")
        except Exception as e:
            print(f"❌ Finnhub test failed: {e}")
    else:
        print("❌ No Finnhub token found")
    
    # Test Tradier
    print("\n2. Testing Tradier:")
    tradier_token = os.getenv('TRADIER_API_TOKEN')
    if tradier_token:
        print(f"✅ Token found: {tradier_token[:20]}...")
        try:
            headers = {
                "Authorization": f"Bearer {tradier_token}",
                "Accept": "application/json"
            }
            test_url = "https://api.tradier.com/v1/markets/quotes"
            test_params = {'symbols': 'AAPL'}
            response = requests.get(test_url, headers=headers, params=test_params, timeout=10)
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                print("✅ Tradier API working!")
            else:
                print(f"❌ Tradier API failed: {response.text[:100]}")
        except Exception as e:
            print(f"❌ Tradier test failed: {e}")
    else:
        print("❌ No Tradier token found")
    
    # Test OpenAI
    print("\n3. Testing OpenAI:")
    openai_token = os.getenv('OPENAI_API_KEY')
    if openai_token:
        print(f"✅ Token found: {openai_token[:20]}...")
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_token)
            response = client.chat.completions.create(
                model="gpt-5-nano",
                messages=[{"role": "user", "content": "Say 'test'"}],
            )
            print("✅ OpenAI API working!")
        except Exception as e:
            print(f"❌ OpenAI test failed: {e}")
    else:
        print("❌ No OpenAI token found")

if __name__ == "__main__":
    test_apis()
