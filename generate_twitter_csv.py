#!/usr/bin/env python3
"""
Generate Twitter CSV from morning brief data.
Usage: python generate_twitter_csv.py [json_file]
"""

import json
import os
import sys
import argparse
import csv
from datetime import datetime
from pathlib import Path
from typing import List, Dict

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from daily_brief_schema import MorningBrief

def load_brief_data(json_file: str) -> MorningBrief:
    """Load and validate morning brief data from JSON file."""
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        # Validate with Pydantic
        brief = MorningBrief(**data)
        return brief
        
    except FileNotFoundError:
        print(f"Error: File '{json_file}' not found.")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in '{json_file}': {e}")
        sys.exit(1)
    except Exception as e:
        print(f"Error: Failed to load brief data: {e}")
        sys.exit(1)

def generate_twitter_posts(brief: MorningBrief) -> List[Dict[str, str]]:
    """Generate Twitter posts from morning brief data."""
    posts = []
    
    # 5 one-off posts
    posts.extend([
        {
            "post_text": f"📈 Morning Brief: {brief.subject_theme}\n\n{brief.preheader}",
            "type": "one-off",
            "order": "1"
        },
        {
            "post_text": f"🏠 {brief.macro_data}",
            "type": "one-off", 
            "order": "2"
        },
        {
            "post_text": f"📊 SPY Levels:\nS1: {brief.spy_s1} | S2: {brief.spy_s2}\nR1: {brief.spy_r1} | R2: {brief.spy_r2} | R3: {brief.spy_r3}",
            "type": "one-off",
            "order": "3"
        }
    ])
    
    # Add earnings posts if available
    if brief.earnings:
        earnings_text = "📈 Earnings in Focus:\n"
        for item in brief.earnings:
            earnings_text += f"• {item.ticker}: {item.note[:100]}...\n"
        posts.append({
            "post_text": earnings_text,
            "type": "one-off",
            "order": "4"
        })
    
    # Day plan post
    day_plan_text = "🎯 Day Plan:\n"
    for item in brief.day_plan:
        day_plan_text += f"• {item}\n"
    posts.append({
        "post_text": day_plan_text,
        "type": "one-off",
        "order": "5"
    })
    
    # 6-post thread
    thread_posts = [
        {
            "post_text": f"🧵 Options Plunge Morning Brief Thread\n\n{brief.market_overview}",
            "type": "thread",
            "order": "1"
        },
        {
            "post_text": f"📊 Key Levels to Watch:\n\nSPY: S1 {brief.spy_s1} | S2 {brief.spy_s2} | R1 {brief.spy_r1} | R2 {brief.spy_r2} | R3 {brief.spy_r3}",
            "type": "thread",
            "order": "2"
        }
    ]
    
    # Add earnings to thread if available
    if brief.earnings:
        earnings_thread = "📈 Earnings Highlights:\n"
        for item in brief.earnings:
            earnings_thread += f"• {item.ticker}: {item.note[:80]}...\n"
        thread_posts.append({
            "post_text": earnings_thread,
            "type": "thread",
            "order": "3"
        })
    
    # Day plan thread post
    day_thread = "🎯 Today's Plan:\n"
    for i, item in enumerate(brief.day_plan[:2], 1):  # Limit to 2 items for thread
        day_thread += f"{i}. {item}\n"
    thread_posts.append({
        "post_text": day_thread,
        "type": "thread",
        "order": "4"
    })
    
    # Swing plan thread post
    swing_thread = "📈 Swing Plan:\n"
    for i, item in enumerate(brief.swing_plan[:2], 1):  # Limit to 2 items for thread
        swing_thread += f"{i}. {item}\n"
    thread_posts.append({
        "post_text": swing_thread,
        "type": "thread",
        "order": "5"
    })
    
    # Final thread post
    final_thread = f"🔮 On Deck: {brief.on_deck if brief.on_deck else 'Monitor key levels for breakouts'}\n\n📧 Get the full brief: {brief.cta_url}"
    thread_posts.append({
        "post_text": final_thread,
        "type": "thread",
        "order": "6"
    })
    
    posts.extend(thread_posts)
    return posts

def save_csv(posts: List[Dict[str, str]], date_str: str):
    """Save posts to CSV file."""
    # Create output directory
    output_dir = Path("out/social")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save CSV file
    csv_file = output_dir / f"twitter_posts_{date_str}.csv"
    with open(csv_file, 'w', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=['post_text', 'type', 'order'])
        writer.writeheader()
        writer.writerows(posts)
    
    print(f"Twitter CSV saved to: {csv_file}")
    print(f"Generated {len(posts)} posts ({len([p for p in posts if p['type'] == 'one-off'])} one-offs, {len([p for p in posts if p['type'] == 'thread'])} thread posts)")

def main():
    parser = argparse.ArgumentParser(description="Generate Twitter CSV from morning brief")
    parser.add_argument("json_file", help="Path to JSON file with brief data")
    
    args = parser.parse_args()
    
    # Load and validate brief data
    print(f"Loading brief data from: {args.json_file}")
    brief = load_brief_data(args.json_file)
    
    try:
        # Generate Twitter posts
        print("Generating Twitter posts...")
        posts = generate_twitter_posts(brief)
        
        # Save to CSV
        date_str = datetime.now().strftime("%Y-%m-%d")
        save_csv(posts, date_str)
        
        print("✓ Twitter CSV generated successfully")
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()



