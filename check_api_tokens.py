#!/usr/bin/env python3

import os
import requests
from dotenv import load_dotenv

def check_api_tokens():
    """Check all API tokens and their validity"""
    
    print("🔍 Checking API Tokens")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Check Finnhub
    print("\n1. Finnhub Token:")
    finnhub_token = os.getenv('FINNHUB_TOKEN')
    if finnhub_token:
        print(f"✅ Token found: {finnhub_token[:20]}...")
        # Test the token
        try:
            test_url = "https://finnhub.io/api/v1/quote"
            test_params = {'symbol': 'AAPL', 'token': finnhub_token}
            response = requests.get(test_url, params=test_params, timeout=10)
            if response.status_code == 200:
                print("✅ Token is valid!")
            else:
                print(f"❌ Token validation failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Token test failed: {e}")
    else:
        print("❌ No Finnhub token found")
    
    # Check Tradier
    print("\n2. Tradier Token:")
    tradier_token = os.getenv('TRADIER_API_TOKEN')
    if tradier_token:
        print(f"✅ Token found: {tradier_token[:20]}...")
        # Test the token
        try:
            headers = {
                "Authorization": f"Bearer {tradier_token}",
                "Accept": "application/json"
            }
            test_url = "https://api.tradier.com/v1/markets/quotes"
            test_params = {'symbols': 'AAPL'}
            response = requests.get(test_url, headers=headers, params=test_params, timeout=10)
            if response.status_code == 200:
                print("✅ Token is valid!")
            else:
                print(f"❌ Token validation failed: {response.status_code}")
        except Exception as e:
            print(f"❌ Token test failed: {e}")
    else:
        print("❌ No Tradier token found")
    
    # Check OpenAI
    print("\n3. OpenAI Token:")
    openai_token = os.getenv('OPENAI_API_KEY')
    if openai_token:
        print(f"✅ Token found: {openai_token[:20]}...")
        # Test the token
        try:
            from openai import OpenAI
            client = OpenAI(api_key=openai_token)
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[{"role": "user", "content": "test"}],
                max_tokens=5
            )
            print("✅ Token is valid!")
        except Exception as e:
            print(f"❌ Token test failed: {e}")
    else:
        print("❌ No OpenAI token found")

if __name__ == "__main__":
    check_api_tokens()
