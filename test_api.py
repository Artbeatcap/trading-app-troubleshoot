import os
import requests
from dotenv import load_dotenv

load_dotenv()

def test_tradier_api():
    api_key = os.getenv('TRADIER_API_KEY')
    headers = {
        'Authorization': f'Bearer {api_key}',
        'Accept': 'application/json'
    }
    
    # Test stock price
    print("Testing stock price...")
    price_url = "https://api.tradier.com/v1/markets/quotes"
    price_params = {'symbols': 'AA'}
    price_response = requests.get(price_url, params=price_params, headers=headers)
    print("Stock price response:", price_response.text)
    
    # Test options expirations
    print("\nTesting options expirations...")
    exp_url = "https://api.tradier.com/v1/markets/options/expirations"
    exp_params = {'symbol': 'AA'}
    exp_response = requests.get(exp_url, params=exp_params, headers=headers)
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
            chain_response = requests.get(chain_url, params=chain_params, headers=headers)
            print("Options chain response:", chain_response.text)

if __name__ == '__main__':
    test_tradier_api() 