#!/usr/bin/env python3

import os
from dotenv import load_dotenv

def check_env():
    """Check environment variables on server"""
    
    print("🔍 Checking Server Environment Variables")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Check each token
    finnhub_token = os.getenv('FINNHUB_TOKEN')
    tradier_token = os.getenv('TRADIER_API_TOKEN')
    openai_token = os.getenv('OPENAI_API_KEY')
    
    print(f"FINNHUB_TOKEN: {'SET' if finnhub_token else 'NOT SET'}")
    if finnhub_token:
        print(f"  Value: {finnhub_token[:20]}...")
    
    print(f"TRADIER_API_TOKEN: {'SET' if tradier_token else 'NOT SET'}")
    if tradier_token:
        print(f"  Value: {tradier_token[:20]}...")
    
    print(f"OPENAI_API_KEY: {'SET' if openai_token else 'NOT SET'}")
    if openai_token:
        print(f"  Value: {openai_token[:20]}...")
    
    # Test API calls
    print("\n🧪 Testing API Calls:")
    
    # Test Finnhub
    if finnhub_token:
        try:
            import requests
            test_url = "https://finnhub.io/api/v1/quote"
            test_params = {'symbol': 'AAPL', 'token': finnhub_token}
            response = requests.get(test_url, params=test_params, timeout=10)
            print(f"Finnhub API: {'✅ WORKING' if response.status_code == 200 else f'❌ FAILED ({response.status_code})'}")
        except Exception as e:
            print(f"Finnhub API: ❌ ERROR - {e}")
    else:
        print("Finnhub API: ❌ NO TOKEN")
    
    # Test Tradier
    if tradier_token:
        try:
            import requests
            headers = {
                "Authorization": f"Bearer {tradier_token}",
                "Accept": "application/json"
            }
            test_url = "https://api.tradier.com/v1/markets/quotes"
            test_params = {'symbols': 'AAPL'}
            response = requests.get(test_url, headers=headers, params=test_params, timeout=10)
            print(f"Tradier API: {'✅ WORKING' if response.status_code == 200 else f'❌ FAILED ({response.status_code})'}")
        except Exception as e:
            print(f"Tradier API: ❌ ERROR - {e}")
    else:
        print("Tradier API: ❌ NO TOKEN")
    
    # Test OpenAI
    if openai_token:
        try:
            import requests
            headers = {
                "Authorization": f"Bearer {openai_token}",
                "Content-Type": "application/json"
            }
            data = {
                "model": "gpt-5-nano",
                "messages": [{"role": "user", "content": "test"}],
                "max_tokens": 5
            }
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers=headers,
                json=data,
                timeout=30
            )
            print(f"OpenAI API: {'✅ WORKING' if response.status_code == 200 else f'❌ FAILED ({response.status_code})'}")
        except Exception as e:
            print(f"OpenAI API: ❌ ERROR - {e}")
    else:
        print("OpenAI API: ❌ NO TOKEN")

if __name__ == "__main__":
    check_env()
