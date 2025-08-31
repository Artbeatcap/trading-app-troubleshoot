#!/usr/bin/env python3
"""
CLI script to send morning brief emails.
Usage: python send_morning_brief.py [json_file] [--dry-run]
"""

import json
import os
import sys
import argparse
from datetime import datetime
from pathlib import Path
from typing import Optional

# Add the current directory to Python path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# NOTE: now use unified builder with mover enrichment
from daily_brief.build import build_context
from emailer import render_morning_brief, send_morning_brief_direct

# Deprecated loader removed; handled by build_context

def save_dry_run_output(html_content: str, text_content: str, date_str: str):
    """Save dry-run output to files."""
    # Create output directory
    output_dir = Path("out/emails") / date_str
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Save HTML file
    html_file = output_dir / "morning_brief.html"
    with open(html_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # Save text file
    text_file = output_dir / "morning_brief.txt"
    with open(text_file, 'w', encoding='utf-8') as f:
        f.write(text_content)
    
    print(f"Dry-run output saved to:")
    print(f"  HTML: {html_file}")
    print(f"  Text: {text_file}")

# -------------------------------------------------------------------------
# Main CLI
# -------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Build and send Options Plunge Morning Brief")
    parser.add_argument("--source", required=True, help="Base JSON file for brief")
    parser.add_argument("--dry-run", action="store_true", help="Write files to out/emails/YYYY-MM-DD but do not send")
    parser.add_argument("--skip-movers", action="store_true", help="Skip building mover lists (faster, offline)")
    parser.add_argument("--test-email", help="Email address for a single test send (overrides subscriber list)")

    args = parser.parse_args()

    # Build context (validation inside build_context)
    include_movers = not args.skip_movers
    print(f"Building context from {args.source} (include movers: {include_movers})")
    context = build_context(args.source, include_movers=include_movers)

    subject = f"Options Plunge Morning Brief — {context['subject_theme']} ({context['date']})"
    
    try:
        # Render email templates
        print("Rendering email templates...")
        html_content, text_content = render_morning_brief(context)
        print("✓ Templates rendered successfully")
        
        if args.dry_run:
            date_str = datetime.now().strftime("%Y-%m-%d")
            save_dry_run_output(html_content, text_content, date_str)
            print("✓ Dry-run completed successfully")
            return
        
        # Determine recipients
        if args.test_email:
            recipients = [args.test_email]
            print(f"Sending test email to: {args.test_email}")
        else:
            # Get recipients from environment
            newsletter_to = os.getenv("NEWSLETTER_TO")
            if not newsletter_to:
                print("Error: NEWSLETTER_TO environment variable not set")
                sys.exit(1)
            
            recipients = [email.strip() for email in newsletter_to.split(',')]
            print(f"Sending to {len(recipients)} recipients")
        
        # Check for confirmation if not test email
        if not args.test_email:
            confirm_send = os.getenv('CONFIRM_SEND')
            if confirm_send != '1':
                print("Error: CONFIRM_SEND=1 environment variable required for production sends")
                print("Set CONFIRM_SEND=1 to confirm you want to send to all subscribers")
                sys.exit(1)
        
        # Send email
        print("Sending email...")
        success = send_morning_brief_direct(html_content, text_content, subject, recipients)
        
        if success:
            print("✓ Morning brief sent successfully")
        else:
            print("✗ Failed to send morning brief")
            sys.exit(1)
            
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
