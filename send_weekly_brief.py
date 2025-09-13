#!/usr/bin/env python3
"""
Weekly Market Brief Sender

Loads weekly brief data from JSON, validates with schema, and sends to users
subscribed to weekly emails.
"""

import os
import sys
import json
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Optional

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from weekly_brief_schema import WeeklyBrief
from emailer import render_weekly_brief, send_weekly_brief_direct
from models import MarketBrief
from datetime import date
import json

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def load_weekly_brief(source_path: str) -> WeeklyBrief:
    """Load and validate weekly brief data from JSON file."""
    try:
        with open(source_path, 'r') as f:
            data = json.load(f)
        
        # Validate with Pydantic schema
        brief = WeeklyBrief(**data)
        logger.info(f"✅ Loaded weekly brief: {brief.subject_theme}")
        return brief
        
    except FileNotFoundError:
        logger.error(f"❌ Source file not found: {source_path}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        logger.error(f"❌ Invalid JSON in {source_path}: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Validation error: {e}")
        sys.exit(1)

def get_weekly_subscribers() -> List[str]:
    """Get list of users subscribed to weekly emails."""
    try:
        # Use Flask ORM instead of raw SQL to avoid connection issues
        from app import app, db
        from models import User
        
        with app.app_context():
            subscribers = User.query.filter(
                User.is_subscribed_weekly == True,
                User.email_verified == True
            ).all()
            
            emails = [user.email for user in subscribers]
            logger.info(f"📧 Found {len(emails)} weekly subscribers")
            return emails
            
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        return []

def save_delivery_log(user_id: int, kind: str, subject: str, provider_id: Optional[str] = None):
    """Log email delivery to database."""
    try:
        # Use Flask ORM instead of raw SQL
        from app import app, db
        from models import EmailDelivery
        
        with app.app_context():
            delivery = EmailDelivery(
                user_id=user_id,
                kind=kind,
                subject=subject,
                provider_id=provider_id
            )
            db.session.add(delivery)
            db.session.commit()
            
    except Exception as e:
        logger.warning(f"⚠️ Could not log delivery: {e}")

def save_dry_run_output(html: str, text: str, date_str: str):
    """Save rendered emails to out/emails/{date}/ directory for dry run."""
    try:
        # Create output directory
        output_dir = Path(f"out/emails/{date_str}")
        output_dir.mkdir(parents=True, exist_ok=True)
        
        # Save HTML version
        html_path = output_dir / "weekly_brief.html"
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html)
        
        # Save text version
        text_path = output_dir / "weekly_brief.txt"
        with open(text_path, 'w', encoding='utf-8') as f:
            f.write(text)
        
        logger.info(f"📁 Dry run output saved to {output_dir}")
        
    except Exception as e:
        logger.error(f"❌ Could not save dry run output: {e}")

def main():
    """Main function to send weekly brief."""
    # Environment diagnostics
    logger.info("🔍 Environment check:")
    logger.info(f"  DATABASE_URL: {'SET' if os.getenv('DATABASE_URL') else 'NOT SET'}")
    logger.info(f"  SENDGRID_API_KEY: {'SET' if os.getenv('SENDGRID_API_KEY') else 'NOT SET'}")
    logger.info(f"  SENDGRID_KEY: {'SET' if os.getenv('SENDGRID_KEY') else 'NOT SET'}")
    logger.info(f"  CONFIRM_SEND: {os.getenv('CONFIRM_SEND', 'NOT SET')}")
    
    parser = argparse.ArgumentParser(description="Send Weekly Market Brief")
    parser.add_argument(
        "--source", 
        required=True,
        help="Path to weekly brief JSON file"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Render emails but don't send (save to out/emails/{date}/)"
    )
    
    args = parser.parse_args()
    
    # Load and validate weekly brief
    brief = load_weekly_brief(args.source)
    
    # Prepare context for template rendering
    context = {
        'subject_theme': brief.subject_theme,
        'date_human': brief.date_human,
        'preheader': brief.preheader,
        'logo_url': brief.logo_url,
        'recap': {
            'index_blurb': brief.recap.index_blurb,
            'sector_blurb': brief.recap.sector_blurb,
            'movers_bullets': brief.recap.movers_bullets,
            'flow_blurb': brief.recap.flow_blurb
        },
        'levels': {
            'spy': brief.levels['spy'].model_dump() if brief.levels.get('spy') else None,
            'qqq': brief.levels['qqq'].model_dump() if brief.levels.get('qqq') else None,
            'iwm': brief.levels['iwm'].model_dump() if brief.levels.get('iwm') else None
        },
        'week_ahead': {
            'macro_bullets': brief.week_ahead.macro_bullets,
            'earnings_bullets': brief.week_ahead.earnings_bullets
        },
        'swing_playbook_bullets': brief.swing_playbook_bullets,
        'cta_url': brief.cta_url,
        'unsubscribe_url': '#',
        'preferences_url': '#'
    }
    
    # Render email templates
    try:
        html_content, text_content = render_weekly_brief(context)
        logger.info("✅ Email templates rendered successfully")
    except Exception as e:
        logger.error(f"❌ Template rendering failed: {e}")
        sys.exit(1)
    
    # Generate subject line
    subject = f"Options Plunge Weekly Brief — {brief.subject_theme} ({brief.date_human})"
    
    # Store brief in database
    try:
        from app import app, db
        with app.app_context():
            # Check if brief already exists for this date
            existing_brief = MarketBrief.query.filter_by(
                brief_type='weekly',
                date=date.today()
            ).first()
            
            if not existing_brief:
                # Store new brief
                market_brief = MarketBrief(
                    brief_type='weekly',
                    date=date.today(),
                    subject=subject,
                    html_content=html_content,
                    text_content=text_content,
                    json_data=json.dumps(brief.model_dump())
                )
                db.session.add(market_brief)
                db.session.commit()
                logger.info("✅ Weekly brief stored in database")
            else:
                logger.info("⚠️ Weekly brief already exists for today")
    except Exception as e:
        logger.warning(f"⚠️ Could not store brief in database: {e}")
    
    if args.dry_run:
        # Save to output directory
        date_str = datetime.now().strftime("%Y-%m-%d")
        save_dry_run_output(html_content, text_content, date_str)
        logger.info("✅ Dry run completed - emails saved to out/emails/")
        return
    
    # Check for confirmation
    if not os.getenv('CONFIRM_SEND'):
        logger.error("❌ CONFIRM_SEND environment variable not set. Set to '1' to confirm sending.")
        logger.info("💡 Run with --dry-run to preview emails first")
        logger.info("💡 Set CONFIRM_SEND=1 in your environment or scheduler")
        sys.exit(1)
    
    # Get subscribers
    subscribers = get_weekly_subscribers()
    if not subscribers:
        logger.warning("⚠️ No weekly subscribers found")
        return
    
    # Send emails
    logger.info(f"📧 Sending weekly brief to {len(subscribers)} subscribers...")
    
    success_count = 0
    for email in subscribers:
        try:
            # Send email
            success = send_weekly_brief_direct(
                html=html_content,
                text=text_content,
                subject=subject,
                to_list=[email]
            )
            
            if success:
                success_count += 1
                logger.info(f"✅ Sent to {email}")
            else:
                logger.error(f"❌ Failed to send to {email}")
                
        except Exception as e:
            logger.error(f"❌ Error sending to {email}: {e}")
    
    logger.info(f"📊 Weekly brief delivery complete: {success_count}/{len(subscribers)} successful")

if __name__ == "__main__":
    main()
