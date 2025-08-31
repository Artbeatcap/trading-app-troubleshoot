#!/usr/bin/env python3
"""
Script to populate sample historical market briefs for testing
"""

import os
import sys
from datetime import date, timedelta
import json
from app import app, db
from models import MarketBrief
from weekly_brief_schema import WeeklyBrief

def create_sample_weekly_briefs():
    """Create sample weekly briefs for the last 4 weeks"""
    with app.app_context():
        # Sample weekly brief data
        sample_data = {
            "subject_theme": "Recap & Week Ahead",
            "preheader": "Your weekly market recap and what's ahead",
            "logo_url": "",
            "recap": {
                "index_blurb": "SPY gained 2.3% last week, with tech leading the charge. Breadth improved as 65% of S&P 500 stocks closed above their 50-day moving averages.",
                "sector_blurb": "Technology and communication services led gains, while utilities lagged. AI momentum continued with NVIDIA and semiconductor stocks surging.",
                "movers_bullets": [
                    "NVDA +8.2% - AI chip demand surge",
                    "TSLA +5.1% - Model 3 refresh announced",
                    "AAPL +3.2% - iPhone 15 pre-orders strong",
                    "META +4.7% - Reels monetization improving",
                    "AMZN +2.8% - AWS growth accelerating"
                ],
                "flow_blurb": "Put/call ratio dropped to 0.65, showing bullish sentiment. Notable flow into NVDA calls and SPY calls for September expiration."
            },
            "levels": {
                "spy": {
                    "s1": "445.50",
                    "s2": "442.20",
                    "r1": "451.80",
                    "r2": "455.10",
                    "r3": "458.40"
                },
                "qqq": {
                    "s1": "375.20",
                    "s2": "371.50",
                    "r1": "382.10",
                    "r2": "385.80",
                    "r3": "389.20"
                }
            },
            "week_ahead": {
                "macro_bullets": [
                    "Tue 2:00 PM ET - Fed Chair Powell speech at Jackson Hole",
                    "Thu 8:30 AM ET - Initial jobless claims",
                    "Fri 8:30 AM ET - PCE inflation data"
                ],
                "earnings_bullets": [
                    "Mon 4:05 PM ET - NVDA earnings",
                    "Wed 4:05 PM ET - SNOW earnings",
                    "Thu 4:05 PM ET - CRM earnings"
                ]
            },
            "swing_playbook_bullets": [
                "Long NVDA calls ahead of earnings - support at $440",
                "SPY bull put spreads at $445/$440 - risk $2.50",
                "QQQ diagonal calls - sell weekly, buy monthly"
            ],
            "cta_url": "https://optionsplunge.com/market-brief"
        }
        
        # Create briefs for the last 4 weeks
        for i in range(4):
            brief_date = date.today() - timedelta(weeks=i+1)
            
            # Check if brief already exists
            existing = MarketBrief.query.filter_by(
                brief_type='weekly',
                date=brief_date
            ).first()
            
            if existing:
                print(f"⚠️ Weekly brief for {brief_date} already exists, skipping...")
                continue
            
            # Update date for this brief
            sample_data["date_human"] = brief_date.strftime("%b %d, %Y")
            
            # Create brief object
            brief = WeeklyBrief(**sample_data)
            
            # Render HTML and text
            from emailer import render_weekly_brief
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
            
            html_content, text_content = render_weekly_brief(context)
            subject = f"Options Plunge Weekly Brief — {brief.subject_theme} ({brief.date_human})"
            
            # Store in database
            market_brief = MarketBrief(
                brief_type='weekly',
                date=brief_date,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                json_data=json.dumps(brief.model_dump())
            )
            
            db.session.add(market_brief)
            print(f"✅ Created weekly brief for {brief_date}")
        
        db.session.commit()
        print("✅ Sample weekly briefs created successfully!")

def create_sample_daily_briefs():
    """Create sample daily briefs for the last 7 days"""
    with app.app_context():
        # Sample daily brief HTML (simplified)
        sample_html = """
        <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto;">
            <h2>Morning Market Brief</h2>
            <p><strong>Market Overview:</strong> Markets opened higher following positive earnings reports from major tech companies.</p>
            <p><strong>Key Levels:</strong> SPY support at $445, resistance at $455</p>
            <p><strong>Today's Focus:</strong> Fed minutes release at 2 PM ET</p>
            <p><strong>Trading Setup:</strong> Bull put spreads on SPY with support at $445</p>
        </div>
        """
        
        sample_text = """
        Morning Market Brief
        
        Market Overview: Markets opened higher following positive earnings reports from major tech companies.
        Key Levels: SPY support at $445, resistance at $455
        Today's Focus: Fed minutes release at 2 PM ET
        Trading Setup: Bull put spreads on SPY with support at $445
        """
        
        # Create briefs for the last 7 days
        for i in range(7):
            brief_date = date.today() - timedelta(days=i+1)
            
            # Skip weekends
            if brief_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
                continue
            
            # Check if brief already exists
            existing = MarketBrief.query.filter_by(
                brief_type='daily',
                date=brief_date
            ).first()
            
            if existing:
                print(f"⚠️ Daily brief for {brief_date} already exists, skipping...")
                continue
            
            subject = f"Options Plunge Morning Brief — Market Update ({brief_date.strftime('%b %d, %Y')})"
            
            # Store in database
            market_brief = MarketBrief(
                brief_type='daily',
                date=brief_date,
                subject=subject,
                html_content=sample_html,
                text_content=sample_text,
                json_data=json.dumps({"date": brief_date.isoformat()})
            )
            
            db.session.add(market_brief)
            print(f"✅ Created daily brief for {brief_date}")
        
        db.session.commit()
        print("✅ Sample daily briefs created successfully!")

if __name__ == "__main__":
    print("📊 Creating sample market briefs...")
    create_sample_weekly_briefs()
    create_sample_daily_briefs()
    print("🎉 Sample briefs population complete!")
