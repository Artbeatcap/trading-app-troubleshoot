import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()
print("Environment variables loaded from .env file")

# Check Tradier API variables
tradier_token = os.getenv('TRADIER_API_TOKEN')
tradier_base_url = os.getenv('TRADIER_API_BASE_URL')

print("\nTradier API Configuration:")
print(f"TRADIER_API_TOKEN: {'Set' if tradier_token else 'Not set'}")
print(f"TRADIER_API_BASE_URL: {tradier_base_url}")

# Print actual values (masked for security)
if tradier_token:
    masked_token = tradier_token[:4] + '*' * (len(tradier_token) - 8) + tradier_token[-4:]
    print(f"Masked TRADIER_API_TOKEN: {masked_token}")
