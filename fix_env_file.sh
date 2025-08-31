#!/bin/bash

echo "🔧 Fixing .env file line endings..."
cd /home/tradingapp/trading-analysis

# Check if dos2unix is available
if command -v dos2unix &> /dev/null; then
    dos2unix .env
    echo "✅ Used dos2unix to fix line endings"
else
    # Alternative: use sed to remove carriage returns
    sed -i 's/\r$//' .env
    echo "✅ Used sed to remove carriage returns"
fi

echo -e "\n🔍 Testing Finnhub token after fix:"
source .env
echo "Token: '$FINNHUB_TOKEN'"
echo "Token length: ${#FINNHUB_TOKEN}"

echo -e "\n🧪 Testing Finnhub API call:"
curl -sS "https://finnhub.io/api/v1/quote?symbol=AAPL&token=$FINNHUB_TOKEN"
