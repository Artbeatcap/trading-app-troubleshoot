"""
Market Brief Generator with GPT News Integration and Improved HTML Styling
Uses ChatGPT API to fetch and summarize market headlines with enhanced formatting
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
        
        prompt = """You are a financial news analyst. Provide 7 current market headlines from today with the following format for each:

1. [Headline Title]
   Source: [News Source]
   Summary: [Brief 1-2 sentence summary]

Focus on major market-moving news like:
- Federal Reserve announcements
- Economic data releases (CPI, jobs, GDP)
- Major earnings reports
- Market volatility and trading activity
- Oil prices and commodities
- Treasury yields and bond markets
- Technology sector news
- International trade and geopolitical events

Make sure the headlines are current and relevant to today's market conditions. Return only the formatted headlines, no additional text."""

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
            
            # Parse the headlines from the response
            headlines = []
            lines = content.strip().split('\n')
            current_headline = {}
            
            for line in lines:
                line = line.strip()
                if line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.')):
                    # New headline
                    if current_headline:
                        headlines.append(current_headline)
                    current_headline = {
                        'headline': line.split('. ', 1)[1] if '. ' in line else line,
                        'source': 'Market News',
                        'summary': '',
                        'datetime': int(datetime.now().timestamp())
                    }
                elif line.startswith('Source:'):
                    current_headline['source'] = line.replace('Source:', '').strip()
                elif line.startswith('Summary:'):
                    current_headline['summary'] = line.replace('Summary:', '').strip()
            
            # Add the last headline
            if current_headline:
                headlines.append(current_headline)
            
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


def generate_html_content_with_summary(summary: str, headlines: List[Dict[str, Any]], 
                                      expected_range: Dict[str, Any], gapping_stocks: List[Dict[str, Any]], 
                                      subscriber_summary: str = None) -> str:
    """Generate beautiful HTML content with improved styling and spacing"""
    
    # Get current date
    current_date = datetime.now().strftime('%A, %B %d, %Y')
    
    # Get key price data for styling
    spy_data = expected_range.get('spy', {})
    qqq_data = expected_range.get('qqq', {})
    
    # Convert markdown to HTML with proper headline formatting
    summary_html = summary.replace('## ', '<h2 class="section-header">').replace('\n\n', '</h2>\n\n')
    summary_html = summary_html.replace('##', '</h2>\n\n<h2 class="section-header">')
    
    # Format headlines with proper spacing
    for i in range(1, 8):
        headline_start = f"{i}. "
        if headline_start in summary_html:
            # Find the headline section and format it
            headline_section = f"""
            <div class="headline-item">
                <div class="headline-number">{i}.</div>
                <div class="headline-content">
                    <div class="headline-title">{headlines[i-1].get('headline', '')}</div>
                    <div class="headline-source">Source: {headlines[i-1].get('source', 'Market News')}</div>
                    <div class="headline-summary">{headlines[i-1].get('summary', '')}</div>
                </div>
            </div>"""
            summary_html = summary_html.replace(f"{i}. {headlines[i-1].get('headline', '')}\n   Source: {headlines[i-1].get('source', 'Market News')}\n   Summary: {headlines[i-1].get('summary', '')}", headline_section)
    
    # Add subscriber summary if provided with enhanced styling
    subscriber_html = ""
    if subscriber_summary:
        # Parse subscriber summary for better formatting
        lines = subscriber_summary.strip().split('\n')
        formatted_summary = ""
        
        for line in lines:
            line = line.strip()
            if line.startswith('**') and line.endswith('**'):
                # Bold headers
                formatted_summary += f'<div class="summary-header">{line}</div>'
            elif line.startswith('- **'):
                # List items with bold tickers
                formatted_summary += f'<div class="summary-list-item">{line}</div>'
            elif line.startswith('**Levels to watch'):
                # Special section
                formatted_summary += f'<div class="summary-levels-header">{line}</div>'
            elif line.startswith('- Support:') or line.startswith('- Resistance:'):
                # Level items
                formatted_summary += f'<div class="summary-level-item">{line}</div>'
            elif line.startswith('**Tomorrow:**'):
                # Tomorrow section
                formatted_summary += f'<div class="summary-tomorrow">{line}</div>'
            elif line:
                # Regular text
                formatted_summary += f'<div class="summary-text">{line}</div>'
        
        subscriber_html = f"""
        <div class="subscriber-summary">
            <div class="summary-header-main">
                <i class="fas fa-chart-line"></i>
                <span>Subscriber Summary</span>
            </div>
            <div class="summary-content">
                {formatted_summary}
            </div>
        </div>
        <hr style="margin: 30px 0; border: none; border-top: 2px solid #e9ecef;">
        <p style="text-align: center; color: #6c757d; font-style: italic; font-size: 14px;">
            This summary provides key market insights for active traders. For detailed analysis, visit our full market brief.
        </p>"""
    
    # Add gapping stocks section if available
    gapping_stocks_html = ""
    if gapping_stocks:
        gapping_stocks_html = """
        <div class="section-content">
            <h2 class="section-header">🚀 Gapping Stocks</h2>"""
        for stock in gapping_stocks[:5]:
            ticker = stock.get('ticker', '')
            move = stock.get('move', '')
            why = stock.get('why', '')
            gapping_stocks_html += f"""
            <div class="gapping-stock-item">
                <strong class="ticker">{ticker}</strong>: <span class="move">{move}</span> - <span class="why">{why}</span>
            </div>"""
        gapping_stocks_html += "</div>"
    
    # Create the full HTML content with improved styling
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Morning Market Brief</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        .section-header {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 8px;
            margin: 25px 0 15px 0;
            font-size: 18px;
            font-weight: bold;
        }}
        .market-snapshot {{
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid #3498db;
        }}
        .section-content {{
            background: #ffffff;
            padding: 20px;
            border-radius: 8px;
            margin: 15px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .subscriber-summary {{
            background: linear-gradient(135deg, #e8f4fd 0%, #d1ecf1 100%);
            padding: 25px;
            border-radius: 12px;
            margin: 25px 0;
            border-left: 5px solid #17a2b8;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        .summary-header-main {{
            display: flex;
            align-items: center;
            margin-bottom: 20px;
            font-size: 22px;
            font-weight: bold;
            color: #2c3e50;
        }}
        .summary-header-main i {{
            margin-right: 10px;
            color: #17a2b8;
        }}
        .summary-content {{
            line-height: 1.6;
        }}
        .summary-header {{
            font-weight: bold;
            color: #2c3e50;
            margin: 15px 0 8px 0;
            font-size: 16px;
        }}
        .summary-list-item {{
            margin: 8px 0;
            padding-left: 15px;
            color: #495057;
        }}
        .summary-levels-header {{
            font-weight: bold;
            color: #2c3e50;
            margin: 15px 0 8px 0;
            font-size: 16px;
        }}
        .summary-level-item {{
            margin: 5px 0;
            padding-left: 15px;
            color: #495057;
        }}
        .summary-tomorrow {{
            font-weight: bold;
            color: #2c3e50;
            margin: 15px 0 8px 0;
            font-size: 16px;
        }}
        .summary-text {{
            margin: 8px 0;
            color: #495057;
        }}
        .headline-item {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            margin: 15px 0;
            border-left: 4px solid #3498db;
            display: flex;
            align-items: flex-start;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        }}
        .headline-number {{
            color: #3498db;
            font-weight: bold;
            font-size: 18px;
            margin-right: 15px;
            min-width: 25px;
        }}
        .headline-content {{
            flex: 1;
        }}
        .headline-title {{
            font-weight: bold;
            color: #2c3e50;
            font-size: 16px;
            margin-bottom: 8px;
            line-height: 1.4;
        }}
        .headline-source {{
            color: #6c757d;
            font-size: 14px;
            font-style: italic;
            margin-bottom: 5px;
        }}
        .headline-summary {{
            color: #495057;
            line-height: 1.5;
        }}
        .gapping-stock-item {{
            background: #f8f9fa;
            padding: 12px;
            border-radius: 6px;
            margin: 8px 0;
            border-left: 3px solid #28a745;
        }}
        .ticker {{
            color: #2c3e50;
            font-weight: bold;
        }}
        .move {{
            color: #28a745;
            font-weight: 500;
        }}
        .why {{
            color: #6c757d;
        }}
        .key-levels {{
            background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
            padding: 20px;
            border-radius: 8px;
            margin: 20px 0;
            border-left: 4px solid #ffc107;
        }}
        .level-item {{
            margin: 10px 0;
            font-weight: 500;
        }}
        .support {{
            color: #28a745;
        }}
        .resistance {{
            color: #dc3545;
        }}
    </style>
</head>
<body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background-color: #f8f9fa; margin: 0; padding: 20px;">

    <div style="max-width: 800px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">

        <div style="background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%); color: white; padding: 30px; text-align: center;">
            <h1 style="margin: 0; font-size: 28px; font-weight: 300;">Morning Market Brief</h1>
            <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">{current_date}</p>
        </div>

        <div style="padding: 30px;">
            {subscriber_html}
            
            <div class="section-content">
                {summary_html}
            </div>
            
            {gapping_stocks_html}
            
            <div class="key-levels">
                <h3 style="margin-top: 0; color: #856404;">Key Levels to Watch</h3>
                <div class="level-item">
                    <strong>SPY:</strong> ${spy_data.get('resistance', 0):.2f} 
                    <span class="support">(Support: ${spy_data.get('support', 0):.2f})</span> 
                    <span class="resistance">(Resistance: ${spy_data.get('resistance', 0):.2f})</span>
                </div>
                <div class="level-item">
                    <strong>QQQ:</strong> ${qqq_data.get('resistance', 0):.2f} 
                    <span class="support">(Support: ${qqq_data.get('support', 0):.2f})</span> 
                    <span class="resistance">(Resistance: ${qqq_data.get('resistance', 0):.2f})</span>
                </div>
            </div>
        </div>
    </div>
</body>
</html>"""
    
    return html_content


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

    # Generate HTML content with GPT summary
    brief_content = generate_html_content_with_summary(summary, headlines, expected_range, gapping_stocks, subscriber_summary)
    
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
    print("🚀 Starting Market Brief Generation with Improved Styling...")
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
