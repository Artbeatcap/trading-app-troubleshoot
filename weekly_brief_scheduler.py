#!/usr/bin/env python3
"""
Weekly Market Brief Scheduler

Runs every Sunday at 12:00 PM ET to send the weekly market brief.
"""

import os
import sys
import logging
from datetime import datetime
import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from send_weekly_brief import main as send_weekly_brief

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def start_weekly_brief_scheduler():
    """Start the weekly brief scheduler."""
    try:
        # Set timezone to Eastern Time
        tz = pytz.timezone("America/New_York")
        
        # Create scheduler
        scheduler = BackgroundScheduler(timezone=tz)
        
        # Add weekly brief job - Sundays at 12:00 PM ET
        scheduler.add_job(
            func=send_weekly_brief_job,
            trigger=CronTrigger(
                day_of_week="sun",
                hour=12,
                minute=0,
                timezone=tz
            ),
            id="weekly_brief_sunday_noon",
            name="Weekly Market Brief",
            replace_existing=True,
            max_instances=1,
            misfire_grace_time=3600  # 1 hour grace time
        )
        
        # Start scheduler
        scheduler.start()
        logger.info("✅ Weekly brief scheduler started")
        logger.info("📅 Scheduled: Sundays at 12:00 PM ET")
        
        return scheduler
        
    except Exception as e:
        logger.error(f"❌ Failed to start weekly brief scheduler: {e}")
        return None

def send_weekly_brief_job():
    """Job function to send weekly brief."""
    try:
        logger.info("🚀 Starting weekly brief job...")
        
        # Set confirmation flag
        os.environ['CONFIRM_SEND'] = '1'
        
        # Get source file path
        source_file = os.getenv('WEEKLY_BRIEF_SOURCE', 'weekly_brief_sample.json')
        
        # Import and run the main function
        import sys
        sys.argv = ['send_weekly_brief.py', '--source', source_file]
        
        # Run the weekly brief sender
        send_weekly_brief()
        
        logger.info("✅ Weekly brief job completed successfully")
        
    except Exception as e:
        logger.error(f"❌ Weekly brief job failed: {e}")

def main():
    """Main function to run the scheduler."""
    print("📅 Starting Weekly Market Brief Scheduler...")
    print("⏰ Scheduled: Sundays at 12:00 PM ET")
    print("📧 Source: weekly_brief_sample.json")
    print("🔄 Press Ctrl+C to stop")
    
    # Start scheduler
    scheduler = start_weekly_brief_scheduler()
    
    if not scheduler:
        sys.exit(1)
    
    try:
        # Keep the script running
        while True:
            import time
            time.sleep(60)  # Check every minute
            
    except KeyboardInterrupt:
        print("\n🛑 Stopping scheduler...")
        scheduler.shutdown()
        print("✅ Scheduler stopped")

if __name__ == "__main__":
    main()
