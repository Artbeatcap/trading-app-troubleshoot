#!/usr/bin/env python3
"""Check weekly brief subscribers"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from send_weekly_brief import get_weekly_subscribers

def main():
    print("=== WEEKLY SUBSCRIBERS CHECK ===")
    
    subs = get_weekly_subscribers()
    print(f"Total weekly subscribers: {len(subs)}")
    
    if subs:
        print("First 5 subscribers:")
        for i, email in enumerate(subs[:5], 1):
            print(f"  {i}. {email}")
    else:
        print("No weekly subscribers found!")

if __name__ == "__main__":
    main()
