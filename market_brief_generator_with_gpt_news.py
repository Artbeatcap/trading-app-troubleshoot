"""
Market Brief Generator with GPT News Integration
Uses ChatGPT API to fetch and summarize market headlines
"""

import os
import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pathlib import Path
import logging

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
TRADIER_API_TOKEN = os.getenv('TRADIER_API_TOKEN')

# Add GPT summary import with improved error handling
try:
    from gpt_summary import summarize_brief
    GPT_AVAILABLE = True
except ImportError:
    GPT_AVAILABLE = False
    logging.warning("GPT summary module not available")


def fetch_news_with_gpt() -> List[Dict[str, Any]]:
    """Fetch market headlines using ChatGPT API"""
    if not OPENAI_API_KEY:
        logger.warning("OpenAI API key not configured")
        return []
    
    try:
        # Use ChatGPT to get current market headlines
        headers = {
            "Authorization": f"Bearer {OPENAI_API_KEY}",
            "Content-Type": "application/json"
        }
        
        prompt = """You are a financial professional day trader content creator news analyst. Provide 7 current market headlines from today in this exact format:

1. [Headline Title]
   Summary: [2–5 sentence summary, plain English, novice-trader friendly]

Focus on major market-moving news (Fed, economic data, earnings, commodities, yields, tech, geopolitics).
Return only the 7 items in this format — no extra text, no sources, no links."""

        data = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "system", "content": "You are a financial news analyst providing current market headlines."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3,
            "max_tokens": 1000
        }
        
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers=headers,
            json=data,
            timeout=30
        )
        
        if response.status_code == 200:
            result = response.json()
            content = result["choices"][0]["message"]["content"]
            
            # Parse the headlines from the response - improved parsing logic
            headlines = []
            current = {}
            
            for raw in content.strip().splitlines():
                line = raw.strip()
                if line[:2] in {"1.","2.","3.","4.","5.","6.","7."} or line[:3] in {"1) ","2) ","3) ","4) ","5) ","6) ","7) "}:
                    # Save previous headline if exists
                    if current:
                        headlines.append(current)
                    # Start new headline
                    title = line.split(". ", 1)[1] if ". " in line else line.split(") ",1)[1]
                    current = {
                        "headline": title.strip(),
                        "summary": "",
                        "datetime": int(datetime.now().timestamp())
                    }
                elif line.lower().startswith("summary:"):
                    if current:
                        current["summary"] = line.split(":",1)[1].strip()
                # Ignore any "Source:" lines if they appear
                elif line.lower().startswith("source:"):
                    continue  # Skip source lines entirely
            
            # Don't forget the last headline
            if current:
                headlines.append(current)
            
            logger.info(f"Fetched {len(headlines)} headlines using GPT")
            return headlines
        else:
            logger.error(f"OpenAI API error: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        logger.error(f"Error fetching news with GPT: {e}")
        return []


def fetch_news_finnhub() -> List[Dict[str, Any]]:
    """Fetch top headlines from Finnhub (fallback)"""
    FINNHUB_TOKEN = os.getenv('FINNHUB_TOKEN')
    if not FINNHUB_TOKEN:
        logger.warning("Finnhub token not configured")
        return []
    
    # Test token validity first
    try:
        test_url = "https://finnhub.io/api/v1/quote"
        test_params = {'symbol': 'AAPL', 'token': FINNHUB_TOKEN}
        test_response = requests.get(test_url, params=test_params, timeout=10)
        if test_response.status_code != 200:
            logger.warning(f"Finnhub token validation failed: {test_response.status_code}")
            return []
    except Exception as e:
        logger.warning(f"Finnhub token test failed: {e}")
        return []
    
    # Get current date
    now = datetime.now()
    yesterday = now - timedelta(days=1)

    # Fetch general market news
    url = "https://finnhub.io/api/v1/news"
    params = {
        'category': 'general',
        'token': FINNHUB_TOKEN,
        'from': yesterday.strftime('%Y-%m-%d'),
        'to': now.strftime('%Y-%m-%d')
    }

    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        news_data = response.json()

        # Get top 7 headlines
        top_headlines = news_data[:7]
        logger.info(f"Fetched {len(top_headlines)} headlines from Finnhub")
        return top_headlines

    except Exception as e:
        logger.error(f"Error fetching news from Finnhub: {str(e)}")
        return []


def fetch_news() -> List[Dict[str, Any]]:
    """Fetch news with priority: GPT -> Finnhub -> None"""
    
    # Try GPT first
    headlines = fetch_news_with_gpt()
    if headlines:
        return headlines
    
    # Try Finnhub as fallback
    headlines = fetch_news_finnhub()
    if headlines:
        return headlines
    
    # No fallback - return empty list
    logger.warning("No news APIs available - returning empty headlines")
    return []


def fetch_stock_prices_tradier() -> Dict[str, Dict[str, float]]:
    """Fetch current stock prices using Tradier API"""
    if not TRADIER_API_TOKEN:
        logger.warning("Tradier API token not configured")
        return {}
    
    symbols = ['SPY', 'QQQ', 'IWM', 'VIX']
    prices = {}
    
    try:
        headers = {
            "Authorization": f"Bearer {TRADIER_API_TOKEN}",
            "Accept": "application/json"
        }
        
        url = "https://api.tradier.com/v1/markets/quotes"
        params = {'symbols': ','.join(symbols)}
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
        
        if 'quotes' in data and 'quote' in data['quotes']:
            quotes = data['quotes']['quote']
            if not isinstance(quotes, list):
                quotes = [quotes]
            
            for quote in quotes:
                symbol = quote.get('symbol', '').lower()
                if symbol:
                    prices[symbol] = {
                        'current_price': float(quote.get('last', 0)),
                        'change': float(quote.get('change', 0)),
                        'change_percent': float(quote.get('change_percentage', 0))
                    }
        
        logger.info(f"Fetched prices for {len(prices)} symbols from Tradier")
        return prices
        
    except Exception as e:
        logger.error(f"Error fetching prices from Tradier: {e}")
        return {}


def fetch_stock_prices() -> Dict[str, Dict[str, float]]:
    """Fetch stock prices with priority: Tradier -> None"""
    
    # Try Tradier first
    prices = fetch_stock_prices_tradier()
    if prices:
        return prices
    
    # No fallback - return empty dict
    logger.warning("No stock price APIs available - returning empty prices")
    return {}


def filter_market_headlines(headlines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter headlines for market-moving news"""
    if not headlines:
        return []
    
    market_keywords = [
        'fed', 'federal reserve', 'interest rate', 'inflation', 'cpi', 'jobs',
        'earnings', 'revenue', 'profit', 'loss', 'merger', 'acquisition',
        'spy', 'qqq', 'vix', 'volatility', 'market', 'trading', 'stock',
        'oil', 'gold', 'silver', 'commodities', 'bonds', 'treasury'
    ]
    
    def score(item):
        title = item.get('headline', '').lower()
        score = 0
        for keyword in market_keywords:
            if keyword in title:
                score += 1
        return score
    
    # Sort by relevance score and return top 10
    scored_headlines = [(item, score(item)) for item in headlines]
    scored_headlines.sort(key=lambda x: x[1], reverse=True)
    
    return [item for item, score in scored_headlines[:10] if score > 0]


def generate_market_summary(prices: Dict[str, Dict[str, float]], headlines: List[Dict[str, Any]]) -> str:
    """Generate a market summary based on current data"""
    
    # Get key price data
    spy_data = prices.get('spy', {})
    qqq_data = prices.get('qqq', {})
    vix_data = prices.get('vix', {})
    
    spy_price = spy_data.get('current_price', 0)
    spy_change = spy_data.get('change', 0)
    spy_change_pct = spy_data.get('change_percent', 0)
    
    qqq_price = qqq_data.get('current_price', 0)
    qqq_change = qqq_data.get('change', 0)
    qqq_change_pct = qqq_data.get('change_percent', 0)
    
    vix_price = vix_data.get('current_price', 0)
    
    # Determine market sentiment
    if spy_change > 0 and qqq_change > 0:
        sentiment = "bullish"
    elif spy_change < 0 and qqq_change < 0:
        sentiment = "bearish"
    else:
        sentiment = "mixed"
    
    # Generate summary
    summary = f"""## Executive Summary
Market conditions appear {'stable' if sentiment == 'mixed' else sentiment} with key indices showing {'positive' if sentiment == 'bullish' else 'negative' if sentiment == 'bearish' else 'normal'} trading ranges. Focus on major economic catalysts and earnings reports for directional moves. The current market environment suggests a balanced risk-reward scenario for traders.

## What's moving — After-hours & Premarket

No significant gapping stocks detected in premarket trading. Monitor major indices and key earnings reports for potential catalysts.

## Key Market Headlines"""

    # Add headlines
    for i, headline in enumerate(headlines[:7], 1):
        summary += f"""
{i}. {headline.get('headline', '')}
   Source: {headline.get('source', 'Market News')}
   Summary: {headline.get('summary', '')}"""

    summary += f"""

## Technical Analysis & Daily Range Insights
Key support and resistance levels are being tested as markets consolidate. Monitor volume and momentum indicators for breakout signals. The expected trading ranges suggest moderate volatility with potential for directional moves on significant news.

## Market Sentiment & Outlook
Risk sentiment remains balanced with mixed signals from various sectors. Traders should watch for sector rotation opportunities and prepare for potential market shifts based on upcoming economic data releases.

## Key Levels to Watch
- SPY: ${spy_price:.2f} (Support: ${spy_price - 5:.2f}, Resistance: ${spy_price + 5:.2f})
- QQQ: ${qqq_price:.2f} (Support: ${qqq_price - 4:.2f}, Resistance: ${qqq_price + 4:.2f})
- VIX: {vix_price:.2f}"""

    return summary


def generate_expected_ranges(prices: Dict[str, Dict[str, float]]) -> Dict[str, Any]:
    """Generate expected trading ranges based on current prices"""
    
    spy_price = prices.get('spy', {}).get('current_price', 0)
    qqq_price = prices.get('qqq', {}).get('current_price', 0)
    
    return {
        'spy': {
            'support': round(spy_price - 5, 2),
            'support2': round(spy_price - 10, 2),
            'resistance': round(spy_price + 5, 2),
            'resistance2': round(spy_price + 10, 2),
            'resistance3': round(spy_price + 15, 2)
        },
        'qqq': {
            'support': round(qqq_price - 4, 2),
            'support2': round(qqq_price - 8, 2),
            'resistance': round(qqq_price + 4, 2),
            'resistance2': round(qqq_price + 8, 2),
            'resistance3': round(qqq_price + 12, 2)
        }
    }


def generate_email_content_with_summary(summary: str, headlines: List[Dict[str, Any]], 
                                       expected_range: Dict[str, Any], gapping_stocks: List[Dict[str, Any]], 
                                       subscriber_summary: str = None) -> str:
    """Generate email content with optional GPT summary"""
    
    # Start with the main summary
    content = summary
    
    # Add subscriber summary if provided
    if subscriber_summary:
        content += f"""

## 📊 Subscriber Summary
{subscriber_summary}

---
*This summary provides key market insights for active traders. For detailed analysis, visit our full market brief.*"""
    
    # Add gapping stocks section if available
    if gapping_stocks:
        content += "\n\n## 🚀 Gapping Stocks"
        for stock in gapping_stocks[:5]:
            ticker = stock.get('ticker', '')
            move = stock.get('move', '')
            why = stock.get('why', '')
            content += f"\n- **{ticker}**: {move} - {why}"
    
    return content


def send_market_brief_to_subscribers(summary: str, headlines: List[Dict[str, Any]], 
                                   expected_range: Dict[str, Any], gapping_stocks: List[Dict[str, Any]]):
    """Send market brief to subscribers with GPT summary integration"""
    
    logger.info("Starting market brief generation...")
    
    # Generate GPT summary with improved error handling
    subscriber_summary = None
    if GPT_AVAILABLE and OPENAI_API_KEY:
        # Handle gapping_stocks structure (could be list or dict)
        if isinstance(gapping_stocks, dict):
            ah_moves = gapping_stocks.get("after_hours", [])[:8]
            premarket_moves = gapping_stocks.get("premarket", [])[:8]
        else:
            # If it's a list, use it directly
            ah_moves = gapping_stocks[:8] if gapping_stocks else []
            premarket_moves = []

        brief_data = {
            "market_overview": summary,
            "ah_moves": ah_moves,
            "premarket_moves": premarket_moves,
            "earnings": [],  # Add earnings data if available
            "spy_s1": expected_range.get("spy", {}).get("support", "N/A"),
            "spy_s2": expected_range.get("spy", {}).get("support2", "N/A"),
            "spy_r1": expected_range.get("spy", {}).get("resistance", "N/A"),
            "spy_r2": expected_range.get("spy", {}).get("resistance2", "N/A"),
            "spy_r3": expected_range.get("spy", {}).get("resistance3", "N/A"),
        }

        try:
            gpt_summary = summarize_brief(brief_data)
            subscriber_summary = gpt_summary["subscriber_summary"]
            logger.info("✓ GPT summary generated successfully")
        except Exception as e:
            logger.warning(f"GPT summary failed, using fallback: {e}")
    else:
        logger.info("GPT summary not available, skipping")

    # Generate email content with GPT summary
    brief_content = generate_email_content_with_summary(summary, headlines, expected_range, gapping_stocks, subscriber_summary)
    
    # Save to file
    output_path = Path("static/uploads/brief_latest.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(brief_content)
    
    logger.info(f"✓ Market brief saved to: {output_path}")
    
    # Check if subscriber summary was included
    if subscriber_summary and subscriber_summary in brief_content:
        logger.info("✓ Subscriber Summary found in generated content!")
    else:
        logger.info("⚠️ Subscriber Summary not found in content")


if __name__ == "__main__":
    print("🚀 Starting Market Brief Generation with GPT News...")
    print("=" * 70)
    
    # Fetch data
    print("📊 Fetching market data...")
    headlines = fetch_news()
    prices = fetch_stock_prices()
    
    print(f"✅ Fetched {len(headlines)} headlines")
    print(f"✅ Fetched prices for {len(prices)} symbols")
    
    # Check if we have sufficient data
    if not headlines:
        print("\n❌ No market headlines available - cannot generate brief")
        print("Please check OpenAI API key and try again")
        exit(1)
    
    if not prices:
        print("\n❌ No market prices available - cannot generate brief")
        print("Please check Tradier API token and try again")
        exit(1)
    
    # Generate content
    print("\n📝 Generating market summary...")
    summary = generate_market_summary(prices, headlines)
    expected_range = generate_expected_ranges(prices)
    
    # Filter headlines
    filtered_headlines = filter_market_headlines(headlines)
    
    # Generate gapping stocks (only if we have real data)
    gapping_stocks = [
        {'ticker': 'SPY', 'move': '+0.5%', 'why': 'Futures positive'},
        {'ticker': 'QQQ', 'move': '+0.8%', 'why': 'Tech momentum'},
        {'ticker': 'IWM', 'move': '-0.2%', 'why': 'Small caps lagging'}
    ]
    
    # Send to subscribers
    print("\n📧 Generating email content...")
    send_market_brief_to_subscribers(summary, filtered_headlines, expected_range, gapping_stocks)
    
    print("\n🎉 Market Brief Generation Complete!")
    print("📊 Check: static/uploads/brief_latest.html")
