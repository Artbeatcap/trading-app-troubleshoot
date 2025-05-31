import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
print("Environment variables loaded from .env file")

# Check Tradier API variables
tradier_key = os.getenv('TRADIER_API_KEY')
tradier_token = os.getenv('TRADIER_API_TOKEN')
tradier_base_url = os.getenv('TRADIER_API_BASE_URL')

print("\nTradier API Configuration:")
print(f"TRADIER_API_KEY: {'Set' if tradier_key else 'Not set'}")
print(f"TRADIER_API_TOKEN: {'Set' if tradier_token else 'Not set'}")
print(f"TRADIER_API_BASE_URL: {tradier_base_url}")

# Print actual values (masked for security)
if tradier_key:
    masked_key = tradier_key[:4] + '*' * (len(tradier_key) - 8) + tradier_key[-4:]
    print(f"\nMasked TRADIER_API_KEY: {masked_key}")
if tradier_token:
    masked_token = tradier_token[:4] + '*' * (len(tradier_token) - 8) + tradier_token[-4:]
    print(f"Masked TRADIER_API_TOKEN: {masked_token}") 