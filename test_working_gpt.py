#!/usr/bin/env python3

import os
from dotenv import load_dotenv

def test_working_gpt():
    """Test the working GPT summary module"""
    
    print("🧪 Testing Working GPT Summary Module")
    print("=" * 50)
    
    # Load environment variables
    load_dotenv()
    
    # Test the working module
    try:
        from gpt_summary_working import summarize_brief
        print("✅ Working GPT module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import working GPT module: {e}")
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
    
    print("\n📝 Testing summary generation...")
    
    try:
        result = summarize_brief(test_brief)
        print("✅ Summary generated successfully!")
        print("\nSubscriber Summary:")
        print("-" * 30)
        print(result['subscriber_summary'])
        print("\nPreheader:")
        print("-" * 30)
        print(result['preheader_ai'])
        
        # Check if it's AI-generated or fallback
        if "• Today:" in result['subscriber_summary'] and "• Movers:" in result['subscriber_summary']:
            print("\n📊 Summary Type: Fallback (rule-based)")
        else:
            print("\n🤖 Summary Type: AI-generated")
        
    except Exception as e:
        print(f"❌ Error generating summary: {e}")

if __name__ == "__main__":
    test_working_gpt()
