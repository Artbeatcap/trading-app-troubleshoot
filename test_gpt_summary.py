#!/usr/bin/env python3

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Environment variables loaded from .env file")
except ImportError:
    print("⚠️ python-dotenv not available")
except Exception as e:
    print(f"⚠️ Error loading .env: {e}")

def test_gpt_summary():
    """Test the GPT summary functionality"""
    
    try:
        from gpt_summary import summarize_brief
        print("✓ GPT summary module imported successfully")
    except ImportError as e:
        print(f"✗ Failed to import GPT summary module: {e}")
        return
    
    # Sample brief data
    test_brief = {
        'market_overview': 'Markets are showing mixed signals with tech leading gains while energy lags.',
        'ah_moves': [
            {'ticker': 'AAPL', 'move': '+2.5%', 'why': 'Strong earnings beat'},
            {'ticker': 'TSLA', 'move': '+1.8%', 'why': 'EV sales data positive'},
            {'ticker': 'NVDA', 'move': '+3.2%', 'why': 'AI chip demand strong'}
        ],
        'premarket_moves': [
            {'ticker': 'SPY', 'move': '+0.5%', 'why': 'Futures positive'},
            {'ticker': 'QQQ', 'move': '+0.8%', 'why': 'Tech momentum'},
            {'ticker': 'IWM', 'move': '-0.2%', 'why': 'Small caps lagging'}
        ],
        'earnings': [
            {'ticker': 'AAPL', 'note': 'Beat estimates by 15%'},
            {'ticker': 'MSFT', 'note': 'Cloud revenue up 25%'}
        ],
        'spy_s1': '450.50',
        'spy_s2': '448.75',
        'spy_r1': '453.25',
        'spy_r2': '455.00',
        'spy_r3': '457.50'
    }
    
    print("Testing GPT Summary...")
    print("=" * 50)
    
    # Check if OpenAI API key is available
    if not os.getenv('OPENAI_API_KEY'):
        print("⚠️  OPENAI_API_KEY not found in environment")
        print("Testing fallback summary generation...")
    else:
        print(f"✅ OPENAI_API_KEY found: {os.getenv('OPENAI_API_KEY')[:20]}...")
    
    try:
        result = summarize_brief(test_brief)
        print("✓ Summary generated successfully!")
        print("\nSubscriber Summary:")
        print("-" * 30)
        print(result['subscriber_summary'])
        print("\nPreheader:")
        print("-" * 30)
        print(result['preheader_ai'])
        
    except Exception as e:
        print(f"✗ Error: {e}")
        print("This might be due to missing OPENAI_API_KEY or API issues")

if __name__ == "__main__":
    test_gpt_summary()
