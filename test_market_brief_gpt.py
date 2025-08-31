#!/usr/bin/env python3

import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_market_brief_with_gpt():
    """Test market brief generation with GPT summary"""
    
    try:
        from market_brief_generator import fetch_news, filter_market_headlines, summarize_news, generate_email_content_with_summary
        from gpt_summary import summarize_brief
        import logging
        
        logging.basicConfig(level=logging.INFO)
        print("✓ All modules imported successfully")
        
        # Fetch news and generate summary
        print("Fetching news...")
        headlines = fetch_news()
        filtered = filter_market_headlines(headlines)
        summary = summarize_news(filtered, {}, [])
        
        print(f"Generated summary: {summary[:100]}...")
        
        # Generate GPT summary
        print("Generating GPT summary...")
        brief_data = {
            'market_overview': summary,
            'ah_moves': [],
            'premarket_moves': [],
            'earnings': [],
            'spy_s1': '450.50',
            'spy_s2': '448.75',
            'spy_r1': '453.25',
            'spy_r2': '455.00',
            'spy_r3': '457.50'
        }
        
        gpt_result = summarize_brief(brief_data)
        print("✓ GPT Summary generated!")
        print("\nSubscriber Summary:")
        print("-" * 30)
        print(gpt_result['subscriber_summary'])
        
        # Generate email content with GPT summary
        print("\nGenerating email content with GPT summary...")
        email_content = generate_email_content_with_summary(
            summary, filtered, {}, [], gpt_result['subscriber_summary']
        )
        
        print("✓ Email content generated with GPT summary!")
        print(f"Content length: {len(email_content)} characters")
        
        # Save to file
        output_file = Path(__file__).parent / 'static' / 'uploads' / 'brief_latest.html'
        output_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(email_content)
        
        print(f"✓ Market brief saved to: {output_file}")
        
        # Check if subscriber summary is in the content
        if "Subscriber Summary" in email_content:
            print("✓ Subscriber Summary found in generated content!")
        else:
            print("⚠ Subscriber Summary not found in generated content")
            
        return True
        
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    test_market_brief_with_gpt()
