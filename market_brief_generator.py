"""
Market Brief Generator for Trading Analysis App
Integrates with existing stock news email logic and sends to subscribers
"""

import os
import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
import openai
from flask import current_app
from flask_mail import Message
from models import MarketBriefSubscriber, db
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables (same as stock news app)
FINNHUB_TOKEN = os.getenv('FINNHUB_TOKEN')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')


def fetch_news() -> List[Dict[str, Any]]:
    """Fetch top headlines from Finnhub"""
    if not FINNHUB_TOKEN:
        raise ValueError("FINNHUB_TOKEN environment variable not set")

    # Get current date in EST
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
        response = requests.get(url, params=params)
        response.raise_for_status()
        news_data = response.json()

        # Get top 20 headlines
        top_headlines = news_data[:20]
        logger.info(f"Fetched {len(top_headlines)} headlines from Finnhub")
        return top_headlines

    except Exception as e:
        logger.error(f"Error fetching news: {str(e)}")
        raise


def filter_market_headlines(headlines: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter headlines for market-moving news"""
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


def fetch_stock_prices() -> Dict[str, float]:
    """Fetch current stock prices for key indices"""
    if not FINNHUB_TOKEN:
        raise ValueError("FINNHUB_TOKEN environment variable not set")

    symbols = ['SPY', 'QQQ', 'IWM', 'VIX']
    prices = {}

    for symbol in symbols:
        try:
            url = f"https://finnhub.io/api/v1/quote"
            params = {
                'symbol': symbol,
                'token': FINNHUB_TOKEN
            }
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            
            prices[symbol.lower()] = {
                'current_price': data.get('c', 0),
                'change': data.get('d', 0),
                'change_percent': data.get('dp', 0)
            }
        except Exception as e:
            logger.error(f"Error fetching price for {symbol}: {str(e)}")
            prices[symbol.lower()] = {'current_price': 0, 'change': 0, 'change_percent': 0}

    return prices


def calculate_expected_range(stock_prices: Dict[str, float]) -> Dict[str, Any]:
    """Calculate expected daily range based on VIX and historical data"""
    vix = stock_prices.get('vix', {}).get('current_price', 20)
    
    # Simple range calculation based on VIX
    # Higher VIX = wider expected range
    spy_price = stock_prices.get('spy', {}).get('current_price', 400)
    qqq_price = stock_prices.get('qqq', {}).get('current_price', 300)
    
    # Expected daily range as percentage of price
    spy_range_pct = min(max(vix / 100, 0.01), 0.05)  # 1-5% range
    qqq_range_pct = spy_range_pct * 1.2  # QQQ typically more volatile
    
    return {
        'spy': {
            'current_price': spy_price,
            'expected_range': spy_price * spy_range_pct,
            'support': spy_price * (1 - spy_range_pct/2),
            'resistance': spy_price * (1 + spy_range_pct/2)
        },
        'qqq': {
            'current_price': qqq_price,
            'expected_range': qqq_price * qqq_range_pct,
            'support': qqq_price * (1 - qqq_range_pct/2),
            'resistance': qqq_price * (1 + qqq_range_pct/2)
        },
        'vix': stock_prices.get('vix', {})
    }


def summarize_news(headlines: List[Dict[str, Any]], expected_range: Dict[str, Any]) -> str:
    """Generate AI summary of news and market outlook"""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY environment variable not set")

    # Prepare headlines text
    headlines_text = "\n".join([
        f"- {h.get('headline', '')} ({h.get('source', 'Unknown')})"
        for h in headlines[:7]
    ])

    # Market data
    spy_data = expected_range.get('spy', {})
    qqq_data = expected_range.get('qqq', {})
    vix_data = expected_range.get('vix', {})

    prompt = f"""
Generate a concise morning market brief for traders. Include:

EXECUTIVE SUMMARY:
- Overall market sentiment and key themes
- Major catalysts for today

TECHNICAL ANALYSIS:
- Key support/resistance levels
- Expected trading ranges

MARKET SENTIMENT:
- Risk-on vs risk-off indicators
- Sector rotation themes

KEY LEVELS TO WATCH:
- SPY: ${spy_data.get('current_price', 0):.2f} (Support: ${spy_data.get('support', 0):.2f}, Resistance: ${spy_data.get('resistance', 0):.2f})
- QQQ: ${qqq_data.get('current_price', 0):.2f} (Support: ${qqq_data.get('support', 0):.2f}, Resistance: ${qqq_data.get('resistance', 0):.2f})
- VIX: {vix_data.get('current_price', 0):.2f}

TOP HEADLINES:
{headlines_text}

Keep it concise, actionable, and focused on what traders need to know for today's session.
"""

    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a professional market analyst providing concise, actionable morning briefs for day traders."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.7
        )
        
        return response.choices[0].message.content

    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        return "Error generating market summary. Please check the latest news and market data."


def parse_summary_sections(summary: str) -> Dict[str, str]:
    """Parse the AI summary into sections"""
    sections = {
        'executive_summary': '',
        'technical_analysis': '',
        'market_sentiment': '',
        'key_levels': ''
    }
    
    # Simple parsing - look for section headers
    lines = summary.split('\n')
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        if 'executive summary' in line.lower():
            current_section = 'executive_summary'
        elif 'technical analysis' in line.lower():
            current_section = 'technical_analysis'
        elif 'market sentiment' in line.lower():
            current_section = 'market_sentiment'
        elif 'key levels' in line.lower():
            current_section = 'key_levels'
        elif current_section and line:
            sections[current_section] += line + '\n'
    
    return sections


def generate_email_content(summary: str, headlines: List[Dict[str, Any]], expected_range: Dict[str, Any]) -> str:
    """Generate HTML email content"""
    sections = parse_summary_sections(summary)
    
    # Generate headlines HTML
    headlines_html = ""
    for headline in headlines[:7]:
        headlines_html += f"""
        <tr>
            <td style="padding: 8px 0; border-bottom: 1px solid #eee;">
                <strong>{headline.get('headline', '')}</strong><br>
                <small style="color: #666;">{headline.get('source', 'Unknown')}</small>
            </td>
        </tr>
        """
    
    # Market data
    spy_data = expected_range.get('spy', {})
    qqq_data = expected_range.get('qqq', {})
    vix_data = expected_range.get('vix', {})
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Morning Market Brief</title>
    </head>
    <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
        <div style="max-width: 600px; margin: 0 auto; padding: 20px;">
            <h1 style="color: #2c3e50; border-bottom: 3px solid #3498db; padding-bottom: 10px;">
                Morning Market Brief - {datetime.now().strftime('%A, %B %d, %Y')}
            </h1>
            
            <div style="background: #f8f9fa; padding: 15px; border-radius: 5px; margin: 20px 0;">
                <h3 style="margin-top: 0; color: #2c3e50;">Market Snapshot</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    <tr>
                        <td><strong>SPY:</strong> ${spy_data.get('current_price', 0):.2f}</td>
                        <td><strong>QQQ:</strong> ${qqq_data.get('current_price', 0):.2f}</td>
                        <td><strong>VIX:</strong> {vix_data.get('current_price', 0):.2f}</td>
                    </tr>
                </table>
            </div>
            
            <div style="margin: 20px 0;">
                <h3 style="color: #2c3e50;">Executive Summary</h3>
                <p>{sections.get('executive_summary', 'No summary available.')}</p>
            </div>
            
            <div style="margin: 20px 0;">
                <h3 style="color: #2c3e50;">Key Headlines</h3>
                <table style="width: 100%; border-collapse: collapse;">
                    {headlines_html}
                </table>
            </div>
            
            <div style="margin: 20px 0;">
                <h3 style="color: #2c3e50;">Technical Analysis</h3>
                <p>{sections.get('technical_analysis', 'No technical analysis available.')}</p>
            </div>
            
            <div style="margin: 20px 0;">
                <h3 style="color: #2c3e50;">Market Sentiment</h3>
                <p>{sections.get('market_sentiment', 'No sentiment analysis available.')}</p>
            </div>
            
            <div style="margin: 20px 0;">
                <h3 style="color: #2c3e50;">Key Levels to Watch</h3>
                <p>{sections.get('key_levels', 'No key levels available.')}</p>
            </div>
            
            <div style="background: #ecf0f1; padding: 15px; border-radius: 5px; margin: 20px 0; text-align: center;">
                <p style="margin: 0;">
                    <strong>Powered by Options Plunge</strong><br>
                    <a href="https://your-domain.com/market_brief" style="color: #3498db;">Get the full AI Morning Brief for free</a>
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content


def send_market_brief_to_subscribers():
    """Main function to generate and send market brief to all subscribers"""
    try:
        logger.info("Starting market brief generation and distribution")
        
        # Generate the brief
        headlines = fetch_news()
        filtered_headlines = filter_market_headlines(headlines)
        stock_prices = fetch_stock_prices()
        expected_range = calculate_expected_range(stock_prices)
        summary = summarize_news(filtered_headlines, expected_range)
        
        # Generate email content (just the brief content, not the full email)
        brief_content = generate_email_content(summary, filtered_headlines, expected_range)
        
        # Use the new email system to send to confirmed subscribers
        from emails import send_daily_brief_to_subscribers
        success_count = send_daily_brief_to_subscribers(brief_content)
        
        logger.info(f"Market brief sent successfully to {success_count} confirmed subscribers")
        return success_count
        
    except Exception as e:
        logger.error(f"Error in market brief generation: {str(e)}")
        raise


if __name__ == "__main__":
    # For testing outside of Flask context
    send_market_brief_to_subscribers() 