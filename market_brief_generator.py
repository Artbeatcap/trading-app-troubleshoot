"""
Market Brief Generator for Trading Analysis App
Integrates with existing stock news email logic and sends to subscribers
"""

import os
import requests
import json
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pathlib import Path
from openai import OpenAI
from flask import current_app
from flask_mail import Message
from models import MarketBriefSubscriber, db
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables (resolved at runtime to allow config overrides)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
openai_client = None  # Initialize lazily to avoid import issues

# Add GPT summary import
try:
    from gpt_summary import summarize_brief
    GPT_AVAILABLE = True
except ImportError:
    GPT_AVAILABLE = False
    logging.warning("GPT summary module not available")

# Add headline summarizer import
try:
    from headline_summarizer import summarize_headlines
    HEADLINE_SUMMARIZER_AVAILABLE = True
except ImportError:
    HEADLINE_SUMMARIZER_AVAILABLE = False
    logging.warning("Headline summarizer module not available")


def fetch_news() -> List[Dict[str, Any]]:
    """Fetch top headlines - prioritize GPT, then Finnhub, then fallback to sample data"""
    # First try GPT for news headlines
    if os.getenv("OPENAI_API_KEY"):
        gpt_headlines = fetch_news_with_gpt()
        if gpt_headlines:
            return gpt_headlines
    
    # Fallback to Finnhub
    token = (current_app.config.get('FINNHUB_TOKEN') if current_app else None) or os.getenv('FINNHUB_TOKEN')
    
    if token:
        # Test token validity first
        try:
            test_url = "https://finnhub.io/api/v1/quote"
            test_params = {'symbol': 'AAPL', 'token': token}
            test_response = requests.get(test_url, params=test_params, timeout=10)
            if test_response.status_code != 200:
                logger.warning(f"Finnhub token validation failed: {test_response.status_code}")
                token = None
        except Exception as e:
            logger.warning(f"Finnhub token test failed: {e}")
            token = None
    
    if token:
        # Get current date in EST
        now = datetime.now()
        yesterday = now - timedelta(days=1)

        # Fetch general market news
        url = "https://finnhub.io/api/v1/news"
        params = {
            'category': 'general',
            'token': token,
            'from': yesterday.strftime('%Y-%m-%d'),
            'to': now.strftime('%Y-%m-%d')
        }

        try:
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            news_data = response.json()

            # Get top 20 headlines
            top_headlines = news_data[:20]
            logger.info(f"Fetched {len(top_headlines)} headlines from Finnhub")
            return top_headlines

        except Exception as e:
            logger.error(f"Error fetching news from Finnhub: {str(e)}")
            # Fall through to sample data
    
    # Fallback: return sample market headlines
    sample_headlines = [
        {
            'headline': 'Federal Reserve signals potential rate adjustments in upcoming meetings',
            'summary': 'Fed officials discuss economic outlook and monetary policy direction.',
            'datetime': int(datetime.now().timestamp()),
            'source': 'Market News'
        },
        {
            'headline': 'Major tech earnings reports show mixed results for Q4',
            'summary': 'Technology sector performance varies as companies report quarterly results.',
            'datetime': int(datetime.now().timestamp()),
            'source': 'Earnings Report'
        },
        {
            'headline': 'Oil prices stabilize as OPEC+ maintains production targets',
            'summary': 'Energy markets respond to OPEC+ decision on oil production levels.',
            'datetime': int(datetime.now().timestamp()),
            'source': 'Energy News'
        },
        {
            'headline': 'Market volatility increases ahead of key economic data releases',
            'summary': 'Traders prepare for upcoming CPI and jobs report announcements.',
            'datetime': int(datetime.now().timestamp()),
            'source': 'Economic Data'
        },
        {
            'headline': 'Treasury yields fluctuate as investors assess inflation outlook',
            'summary': 'Bond market reacts to changing expectations for interest rate policy.',
            'datetime': int(datetime.now().timestamp()),
            'source': 'Bond Market'
        },
        {
            'headline': 'S&P 500 reaches new highs as earnings season progresses',
            'summary': 'Market momentum continues as corporate earnings exceed expectations.',
            'datetime': int(datetime.now().timestamp()),
            'source': 'Market Update'
        },
        {
            'headline': 'Cryptocurrency markets show increased volatility',
            'summary': 'Digital asset prices fluctuate amid regulatory developments.',
            'datetime': int(datetime.now().timestamp()),
            'source': 'Crypto News'
        }
    ]
    
    logger.info(f"Using {len(sample_headlines)} sample headlines (Finnhub unavailable)")
    return sample_headlines


def fetch_news_with_gpt() -> List[Dict[str, Any]]:
    """Fetch market headlines using ChatGPT API with enhanced summaries (no Source field)"""
    logger = logging.getLogger(__name__)
    
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        logger.warning("No OpenAI API key available")
        return []
    
    try:
        headers = {
            "Authorization": f"Bearer {api_key}",
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
                {"role": "system", "content": "You are a financial news analyst providing current market headlines with trader-friendly summaries."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.7,
            "max_tokens": 1500
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
            
            # Parse the response - improved parsing logic
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
            
            logger.info(f"✅ Generated {len(headlines)} headlines using GPT (no Source field)")
            return headlines[:7]  # Ensure we return exactly 7
            
        else:
            logger.error(f"GPT API error: {response.status_code} - {response.text}")
            return []
            
    except Exception as e:
        logger.error(f"Error fetching news with GPT: {e}")
        return []


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


def fetch_stock_prices_tradier() -> Dict[str, Dict[str, float]]:
    """Fetch current stock prices using Tradier API"""
    tradier_token = os.getenv('TRADIER_API_TOKEN')
    if not tradier_token:
        logger.warning("Tradier API token not configured")
        return {}
    
    symbols = ['SPY', 'QQQ', 'IWM', 'VIX']
    prices = {}
    
    try:
        headers = {
            "Authorization": f"Bearer {tradier_token}",
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

def fetch_stock_prices_finnhub() -> Dict[str, Dict[str, float]]:
    """Fetch current stock prices using Finnhub API"""
    token = (current_app.config.get('FINNHUB_TOKEN') if current_app else None) or os.getenv('FINNHUB_TOKEN')
    if not token:
        logger.warning("Finnhub token not configured")
        return {}
    
    symbols = ['SPY', 'QQQ', 'IWM', 'VIX']
    prices = {}
    
    # Test token validity first
    try:
        test_url = "https://finnhub.io/api/v1/quote"
        test_params = {'symbol': 'AAPL', 'token': token}
        test_response = requests.get(test_url, params=test_params, timeout=10)
        if test_response.status_code != 200:
            logger.warning(f"Finnhub token validation failed: {test_response.status_code}")
            return {}
    except Exception as e:
        logger.warning(f"Finnhub token test failed: {e}")
        return {}
    
    for symbol in symbols:
        try:
            url = "https://finnhub.io/api/v1/quote"
            params = {'symbol': symbol, 'token': token}
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            prices[symbol.lower()] = {
                'current_price': float(data.get('c', 0)),
                'change': float(data.get('d', 0)),
                'change_percent': float(data.get('dp', 0))
            }
        except Exception as e:
            logger.error(f"Error fetching price for {symbol} from Finnhub: {e}")
            prices[symbol.lower()] = {'current_price': 0, 'change': 0, 'change_percent': 0}
    
    logger.info(f"Fetched prices for {len(prices)} symbols from Finnhub")
    return prices

def fetch_stock_prices() -> Dict[str, Dict[str, float]]:
    """Fetch stock prices with priority: Tradier -> Finnhub -> Default values"""
    
    # Try Tradier first
    prices = fetch_stock_prices_tradier()
    if prices:
        return prices
    
    # Try Finnhub as alternative
    prices = fetch_stock_prices_finnhub()
    if prices:
        return prices
    
    # Fallback to yfinance if both APIs failed
    logger.info("Both Tradier and Finnhub failed, trying yfinance fallback")
    symbols = ['SPY', 'QQQ', 'IWM', 'VIX']
    prices = {}
    
    try:
        import yfinance as yf
        for symbol in symbols:
            try:
                t = yf.Ticker(symbol)
                hist = t.history(period="1d")
                if not hist.empty:
                    prices[symbol.lower()] = {
                        'current_price': float(hist['Close'].iloc[-1]),
                        'change': 0.0,
                        'change_percent': 0.0
                    }
                else:
                    logger.warning(f"No yfinance data for {symbol}")
            except Exception as ye:
                logger.error(f"yfinance error for {symbol}: {ye}")
    except ImportError:
        logger.warning("yfinance not available")

    # Set default values for any symbols that don't have prices
    default_prices = {
        'spy': 400.0,
        'qqq': 300.0,
        'iwm': 200.0,
        'vix': 20.0
    }
    
    for symbol in symbols:
        sym_lower = symbol.lower()
        if sym_lower not in prices or prices[sym_lower]['current_price'] == 0:
            prices[sym_lower] = {
                'current_price': default_prices.get(sym_lower, 0),
                'change': 0.0,
                'change_percent': 0.0
            }
            logger.info(f"Using default price for {symbol}: ${default_prices.get(sym_lower, 0)}")

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


async def fetch_gapping_stocks_tradier() -> Dict[str, List[Dict[str, Any]]]:
    """Fetch gapping stocks using Tradier for after-hours and premarket"""
    logger.info("Fetching gapping stocks with Tradier...")
    
    try:
        # Import the movers scan module
        from movers_scan import scan_all_movers
        import pytz
        
        # Define the universe of stocks to scan (same as before)
        universe = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX', 'AMD', 'INTC',
            'CRM', 'ADBE', 'PYPL', 'SQ', 'ZM', 'SHOP', 'SNOW', 'PLTR', 'CRWD', 'ZS',
            'SPOT', 'UBER', 'LYFT', 'DASH', 'RBLX', 'HOOD', 'COIN', 'MSTR', 'RIOT', 'MARA',
            'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BLK', 'AXP', 'V', 'MA', 'DIS',
            'NKE', 'SBUX', 'MCD', 'KO', 'PEP', 'WMT', 'TGT', 'COST', 'HD', 'LOW',
            'JNJ', 'PFE', 'ABBV', 'UNH', 'CVS', 'ANTM', 'CI', 'HUM', 'ELV', 'DHR',
            'PG', 'KO', 'PEP', 'CL', 'ULTA', 'NKE', 'UA', 'LULU', 'PLNT', 'PTON',
            'XOM', 'CVX', 'COP', 'EOG', 'PXD', 'MPC', 'VLO', 'PSX', 'OXY', 'FANG',
            'BA', 'CAT', 'DE', 'MMM', 'GE', 'HON', 'LMT', 'RTX', 'NOC', 'GD',
            'T', 'VZ', 'TMUS', 'CMCSA', 'CHTR', 'DISH', 'PARA', 'FOX', 'NWSA', 'NWS',
            'SPY', 'QQQ', 'IWM', 'VTI', 'VOO', 'VEA', 'VWO', 'BND', 'TLT', 'GLD',
            'SLV', 'USO', 'UNG', 'DBA', 'DBC', 'VNQ', 'XLF', 'XLK', 'XLE', 'XLV',
            'XLI', 'XLP', 'XLY', 'XLU', 'XLB', 'XLC', 'XLRE', 'XBI', 'XHE', 'XOP',
            'XME', 'XRT', 'XHB', 'XSW', 'XPP', 'XPH', 'XTN', 'SOXX', 'SMH', 'XLK'
        ]
        
        # Get current time in EST
        est = pytz.timezone('America/New_York')
        now = datetime.now(est)
        yesterday = now - timedelta(days=1)
        
        # Define time windows
        # After-hours: 4:00 PM - 8:00 PM ET yesterday
        ah_start = int(est.localize(datetime(yesterday.year, yesterday.month, yesterday.day, 16, 0)).timestamp())
        ah_end = int(est.localize(datetime(yesterday.year, yesterday.month, yesterday.day, 20, 0)).timestamp())
        
        # Pre-market: 7:00 AM - 9:24 AM ET today
        pre_start = int(est.localize(datetime(now.year, now.month, now.day, 7, 0)).timestamp())
        pre_end = int(est.localize(datetime(now.year, now.month, now.day, 9, 24)).timestamp())
        
        # Scan for movers using Tradier
        movers = await scan_all_movers(universe, ah_start, ah_end, pre_start, pre_end)
        
        logger.info(f"Tradier scan complete: Found {len(movers.get('after_hours', []))} AH movers, {len(movers.get('premarket', []))} premarket movers")
        
        return movers
        
    except ImportError:
        logger.warning("Tradier movers scan not available, falling back to yfinance")
        return fetch_gapping_stocks_yfinance()
    except Exception as e:
        logger.error(f"Error in Tradier gapping stocks scan: {e}")
        return {
            "after_hours": [],
            "premarket": []
        }

def fetch_gapping_stocks_yfinance() -> List[Dict[str, Any]]:
    """Fallback: Fetch gapping stocks using yfinance for after-hours and premarket"""
    logger.info("Fetching full universe of stocks with yfinance...")
    
    gapping_stocks = []
    
    try:
        import yfinance as yf
        import pandas as pd
        from datetime import datetime, timedelta
        import requests
        
        # Get current time to determine if we're in premarket or after-hours
        now = datetime.now()
        current_hour = now.hour
        
        # Use a comprehensive stock list
        comprehensive_stocks = [
            'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'NFLX', 'AMD', 'INTC',
            'CRM', 'ADBE', 'PYPL', 'SQ', 'ZM', 'SHOP', 'SNOW', 'PLTR', 'CRWD', 'ZS',
            'SPOT', 'UBER', 'LYFT', 'DASH', 'RBLX', 'HOOD', 'COIN', 'MSTR', 'RIOT', 'MARA',
            'JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'BLK', 'AXP', 'V', 'MA', 'DIS',
            'NKE', 'SBUX', 'MCD', 'KO', 'PEP', 'WMT', 'TGT', 'COST', 'HD', 'LOW',
            'JNJ', 'PFE', 'ABBV', 'UNH', 'CVS', 'ANTM', 'CI', 'HUM', 'ELV', 'DHR',
            'PG', 'KO', 'PEP', 'CL', 'ULTA', 'NKE', 'UA', 'LULU', 'PLNT', 'PTON',
            'XOM', 'CVX', 'COP', 'EOG', 'PXD', 'MPC', 'VLO', 'PSX', 'OXY', 'FANG',
            'BA', 'CAT', 'DE', 'MMM', 'GE', 'HON', 'LMT', 'RTX', 'NOC', 'GD',
            'T', 'VZ', 'TMUS', 'CMCSA', 'CHTR', 'DISH', 'PARA', 'FOX', 'NWSA', 'NWS',
            'SPY', 'QQQ', 'IWM', 'VTI', 'VOO', 'VEA', 'VWO', 'BND', 'TLT', 'GLD',
            'SLV', 'USO', 'UNG', 'DBA', 'DBC', 'VNQ', 'XLF', 'XLK', 'XLE', 'XLV',
            'XLI', 'XLP', 'XLY', 'XLU', 'XLB', 'XLC', 'XLRE', 'XBI', 'XHE', 'XOP',
            'XME', 'XRT', 'XHB', 'XSW', 'XPP', 'XPH', 'XTN', 'SOXX', 'SMH', 'XLK'
        ]
        
        logger.info(f"Scanning {len(comprehensive_stocks)} stocks for gapping movers...")
        
        # Scan stocks for gaps (limit to top 100 for performance)
        scanned_count = 0
        for ticker in comprehensive_stocks[:100]:  # Limit to top 100 for performance
            try:
                t = yf.Ticker(ticker)
                
                # Get recent price data
                hist = t.history(period="2d", interval="1d")
                if hist.empty or len(hist) < 2:
                    continue
                
                # Get current price (premarket/after-hours if available)
                current_price = None
                if current_hour < 9 or current_hour >= 16:  # After-hours or premarket
                    try:
                        # Try to get current price
                        info = t.info
                        if 'regularMarketPrice' in info and info['regularMarketPrice']:
                            current_price = info['regularMarketPrice']
                    except:
                        pass
                
                if current_price is None:
                    current_price = hist['Close'].iloc[-1]
                
                # Calculate gap percentage
                prev_close = hist['Close'].iloc[-2]
                gap_pct = ((current_price - prev_close) / prev_close) * 100
                
                # Get volume and market cap for liquidity filtering
                volume = hist['Volume'].iloc[-1] if len(hist) > 0 else 0
                market_cap = 0
                try:
                    market_cap = t.info.get('marketCap', 0) if hasattr(t, 'info') else 0
                except:
                    pass
                
                # Filter for liquid stocks with significant gaps
                # Criteria: >2% gap, >1M volume, >$100M market cap
                if (abs(gap_pct) >= 2.0 and 
                    volume > 1000000 and 
                    market_cap > 100000000):
                    
                    gapping_stocks.append({
                        'ticker': ticker,
                        'current_price': round(current_price, 2),
                        'prev_close': round(prev_close, 2),
                        'gap_pct': round(gap_pct, 2),
                        'volume': volume,
                        'market_cap': market_cap
                    })
                
                scanned_count += 1
                if scanned_count % 20 == 0:
                    logger.info(f"Scanned {scanned_count} stocks, found {len(gapping_stocks)} gappers...")
                
            except Exception as e:
                logger.warning(f"Error fetching data for {ticker}: {e}")
                continue
        
        # Sort by absolute gap percentage (largest moves first)
        gapping_stocks.sort(key=lambda x: abs(x['gap_pct']), reverse=True)
        
        # Return top 15 gapping stocks
        result = gapping_stocks[:15]
        logger.info(f"Full universe scan complete: Found {len(result)} liquid stocks with significant gaps")
        return result
        
    except Exception as e:
        logger.error(f"Error in full universe scan: {e}")
        # Return sample data for testing
        return [
            {
                'ticker': 'TSLA',
                'current_price': 245.50,
                'prev_close': 240.00,
                'gap_pct': 2.29,
                'volume': 50000000,
                'market_cap': 800000000000
            },
            {
                'ticker': 'NVDA',
                'current_price': 890.25,
                'prev_close': 875.00,
                'gap_pct': 1.74,
                'volume': 45000000,
                'market_cap': 2200000000000
            },
            {
                'ticker': 'AAPL',
                'current_price': 175.80,
                'prev_close': 178.50,
                'gap_pct': -1.51,
                'volume': 60000000,
                'market_cap': 2800000000000
            }
        ]

def fetch_gapping_stocks() -> Dict[str, List[Dict[str, Any]]]:
    """Main function to fetch gapping stocks - tries Tradier first, falls back to yfinance"""
    try:
        # Try Tradier first
        import asyncio
        return asyncio.run(fetch_gapping_stocks_tradier())
    except Exception as e:
        logger.warning(f"Tradier gapping stocks failed, using yfinance fallback: {e}")
        return fetch_gapping_stocks_yfinance()


def fetch_stock_news(ticker: str) -> List[Dict[str, Any]]:
    """Fetch recent news for a specific stock ticker with concise reasons"""
    logger = logging.getLogger(__name__)
    
    # Try to get news from Finnhub if available
    token = (current_app.config.get('FINNHUB_TOKEN') if current_app else None) or os.getenv('FINNHUB_TOKEN')
    
    if token:
        try:
            url = "https://finnhub.io/api/v1/company-news"
            params = {
                'symbol': ticker,
                'from': (datetime.now() - timedelta(days=1)).strftime('%Y-%m-%d'),
                'to': datetime.now().strftime('%Y-%m-%d'),
                'token': token
            }
            
            response = requests.get(url, params=params, timeout=10)
            if response.status_code == 200:
                news_data = response.json()
                # Filter and prioritize news that's likely to cause gaps
                prioritized_news = []
                for news in news_data[:10]:  # Check more news items
                    headline = news.get('headline', '').lower()
                    summary = news.get('summary', '').lower()
                    
                    # Keywords that typically cause significant price movements
                    gap_keywords = [
                        'earnings', 'quarterly', 'revenue', 'profit', 'loss', 'beat', 'miss',
                        'upgrade', 'downgrade', 'analyst', 'target', 'price target',
                        'merger', 'acquisition', 'buyout', 'deal', 'partnership',
                        'fda', 'approval', 'clinical', 'trial', 'drug', 'treatment',
                        'layoff', 'restructuring', 'ceo', 'executive', 'resignation',
                        'bankruptcy', 'chapter', 'delisting', 'reverse split',
                        'dividend', 'buyback', 'share repurchase', 'stock split',
                        'guidance', 'forecast', 'outlook', 'expectations'
                    ]
                    
                    # Check if news contains gap-causing keywords
                    if any(keyword in headline or keyword in summary for keyword in gap_keywords):
                        prioritized_news.append(news)
                
                # Return prioritized news or top 3 if no specific gap news found
                return prioritized_news[:3] if prioritized_news else news_data[:3]
                
        except Exception as e:
            logger.warning(f"Error fetching news for {ticker} from Finnhub: {e}")
    
    # Enhanced fallback: return more specific sample news based on ticker
    sample_news = {
        'TSLA': [
            {
                'headline': f'{ticker} announces new battery technology breakthrough',
                'summary': f'{ticker} revealed significant improvements in battery efficiency and range, potentially reducing costs by 15%.',
                'source': 'Company Press Release',
                'datetime': int(datetime.now().timestamp())
            }
        ],
        'NVDA': [
            {
                'headline': f'{ticker} reports strong quarterly earnings',
                'summary': f'{ticker} exceeded analyst expectations with robust AI chip sales, revenue up 25% YoY.',
                'source': 'Earnings Report',
                'datetime': int(datetime.now().timestamp())
            }
        ],
        'AAPL': [
            {
                'headline': f'{ticker} faces supply chain challenges',
                'summary': f'{ticker} reports delays in new product launches due to component shortages, affecting Q4 guidance.',
                'source': 'Market News',
                'datetime': int(datetime.now().timestamp())
            }
        ],
        'META': [
            {
                'headline': f'{ticker} announces AI partnership',
                'summary': f'{ticker} partners with major tech company to develop next-generation AI capabilities.',
                'source': 'Company News',
                'datetime': int(datetime.now().timestamp())
            }
        ],
        'AMZN': [
            {
                'headline': f'{ticker} expands cloud services',
                'summary': f'{ticker} launches new AWS services, expanding market share in cloud computing.',
                'source': 'Business News',
                'datetime': int(datetime.now().timestamp())
            }
        ],
        'GOOGL': [
            {
                'headline': f'{ticker} reports strong ad revenue',
                'summary': f'{ticker} exceeds expectations with robust advertising revenue growth.',
                'source': 'Earnings Report',
                'datetime': int(datetime.now().timestamp())
            }
        ],
        'MSFT': [
            {
                'headline': f'{ticker} cloud business grows',
                'summary': f'{ticker} reports strong Azure growth, beating cloud revenue expectations.',
                'source': 'Earnings Report',
                'datetime': int(datetime.now().timestamp())
            }
        ]
    }
    
    return sample_news.get(ticker, [
        {
            'headline': f'{ticker} shows significant premarket activity',
            'summary': f'{ticker} is experiencing unusual trading volume and price movement, likely due to recent news or market sentiment.',
            'source': 'Market Data',
            'datetime': int(datetime.now().timestamp())
        }
    ])


def generate_gapping_stocks_summary(gapping_stocks: List[Dict[str, Any]]) -> str:
    """Generate AI summary for gapping stocks section"""
    logger = logging.getLogger(__name__)
    
    if not OPENAI_API_KEY:
        return generate_gapping_stocks_fallback(gapping_stocks)
    
    try:
        from openai import OpenAI
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        logger.error(f"Error initializing OpenAI client: {str(e)}")
        return generate_gapping_stocks_fallback(gapping_stocks)
    
    # Prepare stock data with news
    stocks_data = ""
    for i, stock in enumerate(gapping_stocks, 1):
        ticker = stock['ticker']
        gap_pct = stock['gap_pct']
        current_price = stock['current_price']
        prev_close = stock['prev_close']
        
        # Get news for this stock
        news_items = fetch_stock_news(ticker)
        news_text = ""
        for news in news_items[:2]:  # Top 2 news items
            news_text += f"   - {news.get('headline', 'No headline')}\n"
            news_text += f"     Source: {news.get('source', 'Unknown')}\n"
            news_text += f"     Summary: {news.get('summary', 'No summary')}\n\n"
        
        stocks_data += f"{i}. {ticker}\n"
        stocks_data += f"   Gap: {gap_pct:+.2f}% (${current_price:.2f} vs ${prev_close:.2f})\n"
        stocks_data += f"   Recent News:\n{news_text}\n"
    
    prompt = f"""
Create a "What's moving — After-hours & Premarket" section for a morning market brief. 
Format each stock summary with concise, actionable news reasons that explain the gap.

STOCKS WITH SIGNIFICANT GAPS:
{stocks_data}

Please format each stock summary as follows:
1. Company name and ticker as a bold heading
2. Percentage change prominently displayed
3. A concise paragraph (2-3 sentences max) summarizing the news driving the movement:
   - Focus on the specific news/event causing the gap
   - Include key financial figures or metrics if relevant
   - Explain the market reaction and trading implications
   - Keep it brief and actionable

Guidelines:
- Be concise and direct - each summary should be 2-3 sentences maximum
- Focus on the most impactful news that explains the gap
- Include specific numbers/percentages when available
- Explain why traders should care about this movement
- Use professional but accessible language

Make it professional, concise, and actionable for traders. Focus on what's driving the gap and what traders should watch for.
"""

    try:
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional market analyst creating concise stock summaries for a morning brief. Format responses with clear headings and professional tone."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500,
            temperature=0.7
        )
        content = response.choices[0].message.content if response and response.choices else ""
        return content or generate_gapping_stocks_fallback(gapping_stocks)

    except Exception as e:
        logger.error(f"Error generating gapping stocks summary: {str(e)}")
        return generate_gapping_stocks_fallback(gapping_stocks)


def generate_gapping_stocks_fallback(gapping_stocks: List[Dict[str, Any]]) -> str:
    """Generate fallback summary for gapping stocks when OpenAI is unavailable"""
    summary = "## What's moving — After-hours & Premarket\n\n"
    
    for stock in gapping_stocks:
        ticker = stock['ticker']
        gap_pct = stock['gap_pct']
        current_price = stock['current_price']
        prev_close = stock['prev_close']
        
        # Get news for this stock
        news_items = fetch_stock_news(ticker)
        news_summary = news_items[0].get('summary', f'{ticker} showing significant premarket activity') if news_items else f'{ticker} experiencing unusual trading volume'
        
        summary += f"**{ticker}**\n"
        summary += f"**{gap_pct:+.2f}%**\n\n"
        summary += f"{news_summary} The stock is currently trading at ${current_price:.2f} compared to yesterday's close of ${prev_close:.2f}. "
        summary += f"Traders should monitor for follow-through momentum and any additional news catalysts.\n\n"
    
    return summary


def summarize_news(headlines: List[Dict[str, Any]], expected_range: Dict[str, Any], gapping_stocks: List[Dict[str, Any]] = None) -> str:
    """Generate AI summary of news and market outlook using comprehensive analysis"""
    if not OPENAI_API_KEY:
        raise ValueError("OPENAI_API_KEY environment variable not set")
    
    # Initialize OpenAI client lazily
    try:
        from openai import OpenAI
        openai_client = OpenAI(api_key=OPENAI_API_KEY)
    except Exception as e:
        logger.error(f"Error initializing OpenAI client: {str(e)}")
        # Return a fallback summary instead of failing
        return generate_fallback_summary(headlines, expected_range, gapping_stocks)

    # Prepare comprehensive headlines text with summaries
    headlines_text = ""
    for i, headline in enumerate(headlines[:15], 1):  # Top 15 headlines
        headlines_text += f"{i}. {headline.get('headline', 'No headline')}\n"
        headlines_text += f"   Source: {headline.get('source', 'Unknown')}\n"
        headlines_text += f"   Summary: {headline.get('summary', 'No summary')}\n\n"

    # Market data
    spy_data = expected_range.get('spy', {})
    qqq_data = expected_range.get('qqq', {})
    vix_data = expected_range.get('vix', {})

    # Prepare expected range text
    range_text = ""
    for ticker_key in ["spy", "qqq"]:
        if expected_range.get(ticker_key):
            data = expected_range[ticker_key]
            range_text += f"{ticker_key.upper()}: ${data.get('current_price', 0):.2f} (Support: ${data.get('support', 0):.2f}, Resistance: ${data.get('resistance', 0):.2f})\n"
    
    if vix_data.get('current_price'):
        range_text += f"VIX: {vix_data.get('current_price', 0):.2f}\n"

    # Prepare gapping stocks text if available
    gapping_text = ""
    if gapping_stocks:
        gapping_text = "\nGAPPING STOCKS (After-hours & Premarket):\n"
        
        # Handle both list and dict structures
        if isinstance(gapping_stocks, dict):
            # New Tradier structure
            ah_moves = gapping_stocks.get("after_hours", [])
            pre_moves = gapping_stocks.get("premarket", [])
            
            # Add after-hours movers
            if ah_moves:
                gapping_text += "After-hours Movers:\n"
                for stock in ah_moves[:5]:
                    ticker = stock.get('ticker', '')
                    move = stock.get('move', '')
                    why = stock.get('why', '')
                    gapping_text += f"- {ticker}: {move} - {why}\n"
                gapping_text += "\n"
            
            # Add premarket movers
            if pre_moves:
                gapping_text += "Premarket Movers:\n"
                for stock in pre_moves[:5]:
                    ticker = stock.get('ticker', '')
                    move = stock.get('move', '')
                    why = stock.get('why', '')
                    gapping_text += f"- {ticker}: {move} - {why}\n"
                gapping_text += "\n"
        else:
            # Old list structure
            for stock in gapping_stocks[:5]:  # Top 5 gapping stocks
                ticker = stock['ticker']
                gap_pct = stock['gap_pct']
                current_price = stock['current_price']
                prev_close = stock['prev_close']
                gapping_text += f"- {ticker}: {gap_pct:+.2f}% (${current_price:.2f} vs ${prev_close:.2f})\n"

    prompt = f"""
Create a comprehensive Morning Market Brief based on the following information. 
Keep the summary to a maximum of 3 pages (approximately 1500 words).

MARKET HEADLINES:
{headlines_text}

DAILY EXPECTED RANGE:
{range_text}{gapping_text}

Please structure the brief as follows:
1. Executive Summary (2-3 paragraphs)
2. What's moving — After-hours & Premarket (if gapping stocks available)
3. Key Market Headlines (top 5-7 most important)
4. Technical Analysis & Daily Range Insights
5. Market Sentiment & Outlook
6. Key Levels to Watch

Make it professional, concise, and actionable for traders. Focus on what traders need to know for today's session.
"""

    try:
        # openai>=1.x client
        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a professional market analyst creating a daily morning brief for traders."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=2000,
            temperature=0.7
        )
        content = response.choices[0].message.content if response and response.choices else ""
        return content or "No summary generated."

    except Exception as e:
        logger.error(f"Error generating summary: {str(e)}")
        return "Error generating market summary. Please check the latest news and market data."


def parse_summary_sections(summary: str) -> Dict[str, str]:
    """Parse the AI summary into sections"""
    sections = {
        'executive_summary': '',
        'gapping_stocks': '',
        'technical_analysis': '',
        'market_sentiment': '',
        'key_levels': '',
        'headlines': ''
    }
    
    # Split by common section headers
    parts = summary.split('##')
    if len(parts) == 1:
        parts = summary.split('#')
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
            
        lines = part.split('\n')
        if not lines:
            continue
            
        section_title = lines[0].strip().lower()
        section_content = '\n'.join(lines[1:]).strip()
        
        if 'executive summary' in section_title:
            sections['executive_summary'] = section_content
        elif "what's moving" in section_title or 'after-hours' in section_title or 'premarket' in section_title:
            sections['gapping_stocks'] = section_content
        elif 'key market headlines' in section_title or 'key headlines' in section_title:
            sections['headlines'] = section_content
        elif 'technical analysis' in section_title:
            sections['technical_analysis'] = section_content
        elif 'market sentiment' in section_title:
            sections['market_sentiment'] = section_content
        elif 'key levels' in section_title:
            sections['key_levels'] = section_content
    
    # If sections weren't found, try simple parsing
    if not any(sections.values()):
        lines = summary.split('\n')
        current_section = None
        
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            if 'executive summary' in line.lower():
                current_section = 'executive_summary'
            elif "what's moving" in line.lower() or 'after-hours' in line.lower() or 'premarket' in line.lower():
                current_section = 'gapping_stocks'
            elif 'technical analysis' in line.lower():
                current_section = 'technical_analysis'
            elif 'market sentiment' in line.lower():
                current_section = 'market_sentiment'
            elif 'key levels' in line.lower():
                current_section = 'key_levels'
            elif current_section and line:
                sections[current_section] += line + '\n'
    
    # If still no sections found, use the whole summary as executive summary
    if not any(sections.values()):
        sections['executive_summary'] = summary
    
    return sections


def generate_fallback_summary(headlines: List[Dict[str, Any]], expected_range: Dict[str, Any], gapping_stocks: List[Dict[str, Any]] = None) -> str:
    """Generate a fallback summary when OpenAI is not available"""
    spy_data = expected_range.get('spy', {})
    qqq_data = expected_range.get('qqq', {})
    vix_data = expected_range.get('vix', {})
    
    # Get top headlines with summaries
    top_headlines = headlines[:7] if headlines else []
    headlines_text = ""
    for i, headline in enumerate(top_headlines, 1):
        headlines_text += f"{i}. {headline.get('headline', 'No headline')}\n"
        headlines_text += f"   Source: {headline.get('source', 'Unknown')}\n"
        headlines_text += f"   Summary: {headline.get('summary', 'No summary')}\n\n"
    
    # Generate gapping stocks section
    gapping_text = "\n## What's moving — After-hours & Premarket\n\n"
    if gapping_stocks:
        # Handle both list and dict structures
        if isinstance(gapping_stocks, dict):
            # New Tradier structure
            ah_moves = gapping_stocks.get("after_hours", [])
            pre_moves = gapping_stocks.get("premarket", [])
            
            # Add after-hours movers
            if ah_moves:
                gapping_text += "**After-hours Movers:**\n\n"
                for stock in ah_moves[:5]:
                    ticker = stock.get('ticker', '')
                    move = stock.get('move', '')
                    why = stock.get('why', '')
                    gapping_text += f"**{ticker}** {move}\n"
                    gapping_text += f"{why}\n\n"
            
            # Add premarket movers
            if pre_moves:
                gapping_text += "**Premarket Movers:**\n\n"
                for stock in pre_moves[:5]:
                    ticker = stock.get('ticker', '')
                    move = stock.get('move', '')
                    why = stock.get('why', '')
                    gapping_text += f"**{ticker}** {move}\n"
                    gapping_text += f"{why}\n\n"
        else:
            # Old list structure
            for stock in gapping_stocks[:5]:  # Top 5 gapping stocks
                ticker = stock['ticker']
                gap_pct = stock['gap_pct']
                current_price = stock['current_price']
                prev_close = stock['prev_close']
                
                # Get news for this stock
                news_items = fetch_stock_news(ticker)
                news_summary = news_items[0].get('summary', f'{ticker} showing significant premarket activity') if news_items else f'{ticker} experiencing unusual trading volume'
                
                gapping_text += f"**{ticker}**\n"
                gapping_text += f"**{gap_pct:+.2f}%**\n\n"
                gapping_text += f"{news_summary} The stock is currently trading at ${current_price:.2f} compared to yesterday's close of ${prev_close:.2f}. "
                gapping_text += f"Traders should monitor for follow-through momentum and any additional news catalysts.\n\n"
    else:
        gapping_text += "No significant gapping stocks detected in premarket trading. Monitor major indices and key earnings reports for potential catalysts.\n\n"
    
    summary = f"""
## Executive Summary
Market conditions appear stable with key indices showing normal trading ranges. Focus on major economic catalysts and earnings reports for directional moves. The current market environment suggests a balanced risk-reward scenario for traders.{gapping_text}

## Key Market Headlines
{headlines_text}

## Technical Analysis & Daily Range Insights
Key support and resistance levels are being tested as markets consolidate. Monitor volume and momentum indicators for breakout signals. The expected trading ranges suggest moderate volatility with potential for directional moves on significant news.

## Market Sentiment & Outlook
Risk sentiment remains balanced with mixed signals from various sectors. Traders should watch for sector rotation opportunities and prepare for potential market shifts based on upcoming economic data releases.

## Key Levels to Watch
- SPY: ${spy_data.get('current_price', 0):.2f} (Support: ${spy_data.get('support', 0):.2f}, Resistance: ${spy_data.get('resistance', 0):.2f})
- QQQ: ${qqq_data.get('current_price', 0):.2f} (Support: ${qqq_data.get('support', 0):.2f}, Resistance: ${qqq_data.get('resistance', 0):.2f})
- VIX: {vix_data.get('current_price', 0):.2f}

Note: This is a fallback summary. For AI-generated analysis, please check your OpenAI API configuration.
"""
    return summary


def generate_email_content(summary: str, headlines: List[Dict[str, Any]], expected_range: Dict[str, Any], gapping_stocks: List[Dict[str, Any]] = None) -> str:
    """Generate HTML email content"""
    sections = parse_summary_sections(summary)
    
    # Generate headlines HTML with enhanced summaries (no Source field)
    headlines_html = ""
    for i, headline in enumerate(headlines[:7], 1):
        # Use enhanced summary if available, fallback to original summary
        summary_text = (headline.get('summary_2to5') or headline.get('summary') or '').strip()
        headlines_html += f"""
        <tr>
            <td style="padding:12px 0;border-bottom:1px solid #eee;">
                <div style="display:flex;align-items:flex-start;">
                    <span style="background:#3498db;color:#fff;border-radius:50%;width:24px;height:24px;display:flex;align-items:center;justify-content:center;font-size:12px;font-weight:bold;margin-right:12px;flex-shrink:0;">{i}</span>
                    <div style="flex:1;">
                        <strong style="color:#2c3e50;font-size:14px;">{headline.get('headline','')}</strong><br>
                        <span style="color:#34495e;font-size:13px;line-height:1.4;margin-top:4px;display:block;">{summary_text}</span>
                    </div>
                </div>
            </td>
        </tr>"""
    
    # Market data
    spy_data = expected_range.get('spy', {})
    qqq_data = expected_range.get('qqq', {})
    vix_data = expected_range.get('vix', {})
    
    # Format sections with proper HTML
    def format_section_content(content):
        if not content:
            return '<p style="color: #7f8c8d; font-style: italic;">No content available.</p>'
        # Convert line breaks to paragraphs
        paragraphs = content.split('\n\n')
        html_paragraphs = []
        for para in paragraphs:
            if para.strip():
                html_paragraphs.append(f'<p style="margin: 0 0 12px 0;">{para.strip()}</p>')
        return '\n'.join(html_paragraphs) if html_paragraphs else '<p style="color: #7f8c8d; font-style: italic;">No content available.</p>'
    
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8">
        <title>Morning Market Brief</title>
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
        </style>
    </head>
    <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; line-height: 1.6; color: #333; background-color: #f8f9fa; margin: 0; padding: 20px;">
        <div style="max-width: 700px; margin: 0 auto; background: white; border-radius: 12px; overflow: hidden; box-shadow: 0 4px 6px rgba(0,0,0,0.1);">
            <div style="background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%); color: white; padding: 30px; text-align: center;">
                <h1 style="margin: 0; font-size: 28px; font-weight: 300;">Morning Market Brief</h1>
                <p style="margin: 10px 0 0 0; font-size: 16px; opacity: 0.9;">{datetime.now().strftime('%A, %B %d, %Y')}</p>
            </div>
            
            <div class="market-snapshot">
                <h3 style="margin-top: 0; color: #2c3e50; font-size: 20px;">Market Snapshot</h3>
                <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px;">
                    <div style="text-align: center; padding: 15px; background: white; border-radius: 6px;">
                        <div style="font-size: 24px; font-weight: bold; color: #2c3e50;">${spy_data.get('current_price', 0):.2f}</div>
                        <div style="font-size: 14px; color: #7f8c8d;">SPY</div>
                    </div>
                    <div style="text-align: center; padding: 15px; background: white; border-radius: 6px;">
                        <div style="font-size: 24px; font-weight: bold; color: #2c3e50;">${qqq_data.get('current_price', 0):.2f}</div>
                        <div style="font-size: 14px; color: #7f8c8d;">QQQ</div>
                    </div>
                    <div style="text-align: center; padding: 15px; background: white; border-radius: 6px;">
                        <div style="font-size: 24px; font-weight: bold; color: #2c3e50;">{vix_data.get('current_price', 0):.2f}</div>
                        <div style="font-size: 14px; color: #7f8c8d;">VIX</div>
                    </div>
                </div>
            </div>
            
            <div style="padding: 30px;">
                <div class="section-content">
                    <h3 class="section-header">Executive Summary</h3>
                    {format_section_content(sections.get('executive_summary', ''))}
                </div>
                
                <div class="section-content">
                    <h3 class="section-header">What's moving — After-hours & Premarket</h3>
                    {format_section_content(sections.get('gapping_stocks', ''))}
                </div>
                
                <div class="section-content">
                    <h3 class="section-header">Key Market Headlines</h3>
                    <table style="width: 100%; border-collapse: collapse;">
                        {headlines_html}
                    </table>
                </div>
                
                <div class="section-content">
                    <h3 class="section-header">Technical Analysis & Daily Range Insights</h3>
                    {format_section_content(sections.get('technical_analysis', ''))}
                </div>
                
                <div class="section-content">
                    <h3 class="section-header">Market Sentiment & Outlook</h3>
                    {format_section_content(sections.get('market_sentiment', ''))}
                </div>
                
                <div class="section-content">
                    <h3 class="section-header">Key Levels to Watch</h3>
                    {format_section_content(sections.get('key_levels', ''))}
                </div>
            </div>
            
            <div style="background: linear-gradient(135deg, #ecf0f1 0%, #bdc3c7 100%); padding: 25px; text-align: center; border-top: 1px solid #bdc3c7;">
                <p style="margin: 0; font-size: 16px; color: #2c3e50;">
                    <strong>Powered by Options Plunge</strong>
                </p>
                <p style="margin: 5px 0 0 0; font-size: 14px; color: #7f8c8d;">
                    Professional market analysis for informed trading decisions
                </p>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_content


def generate_html_content_with_summary(summary: str, headlines: List[Dict[str, Any]], 
                                      expected_range: Dict[str, Any], gapping_stocks: List[Dict[str, Any]], 
                                      subscriber_summary: str = None) -> str:
    """Generate beautiful HTML content with improved styling and better spacing"""
    # Get current date
    current_date = datetime.now().strftime('%A, %B %d, %Y')
    
    # Get key price data for styling
    spy_data = expected_range.get('spy', {})
    qqq_data = expected_range.get('qqq', {})
    
    # Convert markdown to HTML with proper headline formatting
    summary_html = summary.replace('## ', '<h2 class="section-header">').replace('\n\n', '</h2>\n\n')
    # Fix the conversion to avoid nested tags
    summary_html = summary_html.replace('##', '</h2>\n\n<h2 class="section-header">')
    # Clean up any malformed nested tags
    summary_html = summary_html.replace('<h2 class="section-header"><h2 class="section-header">', '<h2 class="section-header">')
    summary_html = summary_html.replace('</h2></h2>', '</h2>')
    
    # Format headlines with proper spacing - only process if we have headlines
    if headlines:
        # Find the headlines section and replace it with formatted HTML
        headlines_start = summary_html.find('<h2 class="section-header">Key Market Headlines</h2>')
        if headlines_start != -1:
            # Find where the headlines section ends
            headlines_end = summary_html.find('<h2 class="section-header">Technical Analysis', headlines_start)
            if headlines_end == -1:
                headlines_end = len(summary_html)
            
            # Extract the headlines section
            headlines_section = summary_html[headlines_start:headlines_end]
            
            # Create formatted headlines HTML with better spacing (no Source field)
            formatted_headlines = '<h2 class="section-header">Key Market Headlines</h2>'
            for i, headline in enumerate(headlines[:7], 1):
                # Use enhanced summary if available, fallback to original summary
                summary_text = (headline.get('summary_2to5') or headline.get('summary') or '').strip()
                formatted_headlines += f"""
                <div class="headline-item">
                    <div class="headline-number">{i}.</div>
                    <div class="headline-content">
                        <div class="headline-title">{headline.get('headline', '')}</div>
                        <div class="headline-summary">{summary_text}</div>
                    </div>
                </div>"""
            
            # Replace the headlines section
            summary_html = summary_html[:headlines_start] + formatted_headlines + summary_html[headlines_end:]
    
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
        
        # Handle both list and dict structures
        if isinstance(gapping_stocks, dict):
            # New Tradier structure
            ah_moves = gapping_stocks.get("after_hours", [])
            pre_moves = gapping_stocks.get("premarket", [])
            
            # Add after-hours movers
            if ah_moves:
                gapping_stocks_html += '<h3 style="color: #e74c3c; margin: 15px 0 10px 0;">After-hours Movers</h3>'
                for stock in ah_moves[:5]:
                    ticker = stock.get('ticker', '')
                    move = stock.get('move', '')
                    why = stock.get('why', '')
                    gapping_stocks_html += f"""
                    <div class="gapping-stock-item">
                        <strong class="ticker">{ticker}</strong>: <span class="move">{move}</span> - <span class="why">{why}</span>
                    </div>"""
            
            # Add premarket movers
            if pre_moves:
                gapping_stocks_html += '<h3 style="color: #27ae60; margin: 15px 0 10px 0;">Premarket Movers</h3>'
                for stock in pre_moves[:5]:
                    ticker = stock.get('ticker', '')
                    move = stock.get('move', '')
                    why = stock.get('why', '')
                    gapping_stocks_html += f"""
                    <div class="gapping-stock-item">
                        <strong class="ticker">{ticker}</strong>: <span class="move">{move}</span> - <span class="why">{why}</span>
                    </div>"""
        else:
            # Old list structure
            for stock in gapping_stocks[:5]:
                ticker = stock.get('ticker', '')
                move = stock.get('move', '')
                why = stock.get('why', '')
                gapping_stocks_html += f"""
                <div class="gapping-stock-item">
                    <strong class="ticker">{ticker}</strong>: <span class="move">{move}</span> - <span class="why">{why}</span>
                </div>"""
        
        gapping_stocks_html += "</div>"
    
    # Create the full HTML content with improved styling and better spacing
    html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Morning Market Brief</title>
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css">
    <style>
        /* Mobile-first responsive design */
        * {{
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f8f9fa;
            margin: 0;
            padding: 10px;
        }}
        
        .container {{
            max-width: 100%;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        
        .header {{
            background: linear-gradient(135deg, #2c3e50 0%, #3498db 100%);
            color: white;
            padding: 20px;
            text-align: center;
        }}
        
        .header h1 {{
            margin: 0;
            font-size: 24px;
            font-weight: 300;
        }}
        
        .header p {{
            margin: 10px 0 0 0;
            font-size: 14px;
            opacity: 0.9;
        }}
        
        .content {{
            padding: 20px;
        }}
        
        .section-header {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 8px;
            margin: 20px 0 12px 0;
            font-size: 18px;
            font-weight: bold;
        }}
        
        .market-snapshot {{
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            border-left: 4px solid #3498db;
        }}
        
        .section-content {{
            background: #ffffff;
            padding: 15px;
            border-radius: 8px;
            margin: 12px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .subscriber-summary {{
            background: linear-gradient(135deg, #e8f4fd 0%, #d1ecf1 100%);
            padding: 20px;
            border-radius: 12px;
            margin: 20px 0;
            border-left: 5px solid #17a2b8;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        
        .summary-header-main {{
            display: flex;
            align-items: center;
            margin-bottom: 15px;
            font-size: 20px;
            font-weight: bold;
            color: #2c3e50;
        }}
        
        .summary-header-main i {{
            margin-right: 8px;
            color: #17a2b8;
        }}
        
        .summary-content {{
            line-height: 1.6;
        }}
        
        .summary-header {{
            font-weight: bold;
            color: #2c3e50;
            margin: 12px 0 6px 0;
            font-size: 16px;
        }}
        
        .summary-list-item {{
            margin: 6px 0;
            padding-left: 12px;
            color: #495057;
        }}
        
        .summary-levels-header {{
            font-weight: bold;
            color: #2c3e50;
            margin: 12px 0 6px 0;
            font-size: 16px;
        }}
        
        .summary-level-item {{
            margin: 4px 0;
            padding-left: 12px;
            color: #495057;
        }}
        
        .summary-tomorrow {{
            font-weight: bold;
            color: #2c3e50;
            margin: 12px 0 6px 0;
            font-size: 16px;
        }}
        
        .summary-text {{
            margin: 6px 0;
            color: #495057;
        }}
        
        .headline-item {{
            background: #f8f9fa;
            padding: 15px;
            border-radius: 10px;
            margin: 15px 0;
            border-left: 5px solid #3498db;
            display: flex;
            align-items: flex-start;
            box-shadow: 0 3px 6px rgba(0,0,0,0.08);
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}
        
        .headline-item:hover {{
            transform: translateY(-2px);
            box-shadow: 0 5px 12px rgba(0,0,0,0.12);
        }}
        
        .headline-number {{
            color: #3498db;
            font-weight: bold;
            font-size: 18px;
            margin-right: 12px;
            min-width: 28px;
            background: #e3f2fd;
            padding: 6px 10px;
            border-radius: 50%;
            text-align: center;
            flex-shrink: 0;
        }}
        
        .headline-content {{
            flex: 1;
            min-width: 0;
        }}
        
        .headline-title {{
            font-weight: bold;
            color: #2c3e50;
            font-size: 16px;
            margin-bottom: 8px;
            line-height: 1.4;
        }}
        
        .headline-summary {{
            color: #495057;
            line-height: 1.6;
            font-size: 14px;
            margin-top: 6px;
        }}
        
        .gapping-stock-item {{
            background: #f8f9fa;
            padding: 10px;
            border-radius: 6px;
            margin: 6px 0;
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
            padding: 15px;
            border-radius: 8px;
            margin: 15px 0;
            border-left: 4px solid #ffc107;
        }}
        
        .level-item {{
            margin: 8px 0;
            font-weight: 500;
        }}
        
        .support {{
            color: #28a745;
        }}
        
        .resistance {{
            color: #dc3545;
        }}
        
        /* Tablet and desktop styles */
        @media (min-width: 768px) {{
            body {{
                padding: 20px;
            }}
            
            .container {{
                max-width: 800px;
            }}
            
            .header {{
                padding: 30px;
            }}
            
            .header h1 {{
                font-size: 28px;
            }}
            
            .header p {{
                font-size: 16px;
            }}
            
            .content {{
                padding: 30px;
            }}
            
            .section-header {{
                margin: 25px 0 15px 0;
            }}
            
            .market-snapshot {{
                padding: 20px;
                margin: 20px 0;
            }}
            
            .section-content {{
                padding: 20px;
                margin: 15px 0;
            }}
            
            .subscriber-summary {{
                padding: 25px;
                margin: 25px 0;
            }}
            
            .summary-header-main {{
                margin-bottom: 20px;
                font-size: 22px;
            }}
            
            .summary-header-main i {{
                margin-right: 10px;
            }}
            
            .summary-header {{
                margin: 15px 0 8px 0;
            }}
            
            .summary-list-item {{
                margin: 8px 0;
                padding-left: 15px;
            }}
            
            .summary-levels-header {{
                margin: 15px 0 8px 0;
            }}
            
            .summary-level-item {{
                margin: 5px 0;
                padding-left: 15px;
            }}
            
            .summary-tomorrow {{
                margin: 15px 0 8px 0;
            }}
            
            .summary-text {{
                margin: 8px 0;
            }}
            
            .headline-item {{
                padding: 25px;
                margin: 25px 0;
            }}
            
            .headline-number {{
                font-size: 20px;
                margin-right: 20px;
                min-width: 30px;
                padding: 8px 12px;
            }}
            
            .headline-title {{
                font-size: 17px;
                margin-bottom: 10px;
            }}
            
            .headline-summary {{
                font-size: 15px;
                margin-top: 8px;
            }}
            
            .gapping-stock-item {{
                padding: 12px;
                margin: 8px 0;
            }}
            
            .key-levels {{
                padding: 20px;
                margin: 20px 0;
            }}
            
            .level-item {{
                margin: 10px 0;
            }}
        }}
    </style>
</head>
<body>

    <div class="container">

        <div class="header">
            <h1>Morning Market Brief</h1>
            <p>{current_date}</p>
        </div>

        <div class="content">
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


def send_market_brief_to_subscribers():
    """Main function to generate and send market brief to all subscribers"""
    try:
        logger.info("Starting market brief generation and distribution")
        
        # Generate the brief
        headlines = fetch_news()
        filtered_headlines = filter_market_headlines(headlines)
        
        # Enhance headlines with 2-5 sentence summaries
        if HEADLINE_SUMMARIZER_AVAILABLE and OPENAI_API_KEY:
            try:
                filtered_headlines = summarize_headlines(filtered_headlines)
                logger.info("✅ Headlines enhanced with AI summaries")
            except Exception as e:
                logger.warning(f"Headline summarization failed, using original summaries: {e}")
        
        stock_prices = fetch_stock_prices()
        expected_range = calculate_expected_range(stock_prices)
        
        # Fetch gapping stocks for the new section
        gapping_stocks = fetch_gapping_stocks()
        
        # Generate summary with gapping stocks
        summary = summarize_news(filtered_headlines, expected_range, gapping_stocks)
        
        # NEW: Generate GPT summary
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
        brief_content = generate_html_content_with_summary(summary, filtered_headlines, expected_range, gapping_stocks, subscriber_summary)

        # Persist latest brief content to a static file for website display
        try:
            base_dir = Path(__file__).resolve().parent
            out_dir = base_dir / 'static' / 'uploads'
            out_dir.mkdir(parents=True, exist_ok=True)
            latest_file = out_dir / 'brief_latest.html'
            latest_date_file = out_dir / 'brief_latest_date.txt'
            latest_file.write_text(brief_content, encoding='utf-8')
            latest_date_file.write_text(datetime.now().strftime('%Y-%m-%d'), encoding='utf-8')
            logger.info(f"Wrote latest brief HTML to {latest_file}")
        except Exception as write_err:
            logger.warning(f"Failed to write latest brief HTML: {write_err}")
        
        # Use the new email system to send to confirmed subscribers
        from emails import send_daily_brief_direct
        success_count = send_daily_brief_direct(brief_content)
        
        logger.info(f"Market brief sent successfully to {success_count} confirmed subscribers")
        return success_count
        
    except Exception as e:
        logger.error(f"Error in market brief generation: {str(e)}")
        raise


if __name__ == "__main__":
    # For testing outside of Flask context
    try:
        # Import and create Flask app context
        from app import app
        with app.app_context():
            send_market_brief_to_subscribers()
    except ImportError:
        # If app import fails, just generate the brief without sending emails
        logger.info("Running in standalone mode - generating brief content only")
        try:
            # Generate the brief
            headlines = fetch_news()
            filtered_headlines = filter_market_headlines(headlines)
            
            # Enhance headlines with 2-5 sentence summaries
            if HEADLINE_SUMMARIZER_AVAILABLE and OPENAI_API_KEY:
                try:
                    filtered_headlines = summarize_headlines(filtered_headlines)
                    logger.info("✅ Headlines enhanced with AI summaries")
                except Exception as e:
                    logger.warning(f"Headline summarization failed, using original summaries: {e}")
            
            stock_prices = fetch_stock_prices()
            expected_range = calculate_expected_range(stock_prices)
            
            # Fetch gapping stocks for the new section
            gapping_stocks = fetch_gapping_stocks()
            
            # Generate summary with gapping stocks
            summary = summarize_news(filtered_headlines, expected_range, gapping_stocks)
            
            # NEW: Generate GPT summary for standalone mode
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
            brief_content = generate_html_content_with_summary(summary, filtered_headlines, expected_range, gapping_stocks, subscriber_summary)

            # Persist latest brief content to a static file for website display
            try:
                base_dir = Path(__file__).resolve().parent
                out_dir = base_dir / 'static' / 'uploads'
                out_dir.mkdir(parents=True, exist_ok=True)
                latest_file = out_dir / 'brief_latest.html'
                latest_date_file = out_dir / 'brief_latest_date.txt'
                latest_file.write_text(brief_content, encoding='utf-8')
                latest_date_file.write_text(datetime.now().strftime('%Y-%m-%d'), encoding='utf-8')
                logger.info(f"Wrote latest brief HTML to {latest_file}")
                logger.info("Market brief generated successfully in standalone mode")
            except Exception as write_err:
                logger.warning(f"Failed to write latest brief HTML: {write_err}")
        except Exception as e:
            logger.error(f"Error in standalone market brief generation: {str(e)}") 