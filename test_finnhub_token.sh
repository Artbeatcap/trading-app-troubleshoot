#!/bin/bash

echo "🔍 Testing Finnhub Token on VPS"
echo "================================"

echo "1. Token length check:"
echo "$FINNHUB_TOKEN" | sed 's/./&/g' | wc -c

echo -e "\n2. Token value check:"
echo "Token: '$FINNHUB_TOKEN'"

echo -e "\n3. Testing Finnhub API call:"
curl -sS "https://finnhub.io/api/v1/quote?symbol=AAPL&token=$FINNHUB_TOKEN"

echo -e "\n\n4. Checking if token is in .env file:"
if [ -f "/home/tradingapp/trading-analysis/.env" ]; then
    echo "✅ .env file exists"
    grep -i finnhub /home/tradingapp/trading-analysis/.env | head -1
else
    echo "❌ .env file not found"
fi

echo -e "\n5. Testing with source .env:"
cd /home/tradingapp/trading-analysis
source .env
echo "Token after sourcing .env: '$FINNHUB_TOKEN'"
curl -sS "https://finnhub.io/api/v1/quote?symbol=AAPL&token=$FINNHUB_TOKEN"
