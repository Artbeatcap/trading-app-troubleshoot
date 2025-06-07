import os
import requests
import pytest
from dotenv import load_dotenv

load_dotenv()

def test_tradier_api():
    api_token = os.getenv('TRADIER_API_TOKEN')
    if not api_token:
        pytest.skip("TRADIER_API_TOKEN not configured")

    headers = {
        'Authorization': f'Bearer {api_token}',
        'Accept': 'application/json'
    }
    
    # Test stock price
    print("Testing stock price...")
    price_url = "https://api.tradier.com/v1/markets/quotes"
    price_params = {'symbols': 'AA'}
    try:
        price_response = requests.get(price_url, params=price_params, headers=headers, timeout=5)
    except Exception:
        pytest.skip("Network unavailable")
    print("Stock price response:", price_response.text)
    
    # Test options expirations
    print("\nTesting options expirations...")
    exp_url = "https://api.tradier.com/v1/markets/options/expirations"
    exp_params = {'symbol': 'AA'}
    exp_response = requests.get(exp_url, params=exp_params, headers=headers, timeout=5)
    print("Options expirations response:", exp_response.text)
    
    # If we have expirations, test options chain
    if exp_response.status_code == 200:
        exp_data = exp_response.json()
        if 'expirations' in exp_data and exp_data['expirations']:
            first_exp = exp_data['expirations']['date'][0]
            print(f"\nTesting options chain for expiration {first_exp}...")
            chain_url = "https://api.tradier.com/v1/markets/options/chains"
            chain_params = {
                'symbol': 'AA',
                'expiration': first_exp
            }
            chain_response = requests.get(chain_url, params=chain_params, headers=headers, timeout=5)
            print("Options chain response:", chain_response.text)
