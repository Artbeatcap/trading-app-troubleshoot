"""
Task scheduler for automated daily market brief sending
"""
import schedule
import time
import logging
from datetime import datetime
from market_brief_generator import send_market_brief_to_subscribers

logger = logging.getLogger(__name__)

def send_daily_brief():
    """Send the daily market brief to all confirmed subscribers"""
    try:
        logger.info("Starting scheduled daily brief sending")
        success_count = send_market_brief_to_subscribers()
        logger.info(f"Daily brief sent to {success_count} subscribers")
        return success_count
    except Exception as e:
        logger.error(f"Error in scheduled daily brief: {str(e)}")
        return 0

def setup_schedule():
    """Setup the daily schedule for sending market briefs"""
    # Send at 7:00 AM ET (adjust timezone as needed)
    schedule.every().day.at("07:00").do(send_daily_brief)
    
    # Also send at 6:30 AM ET as backup
    schedule.every().day.at("06:30").do(send_daily_brief)
    
    logger.info("Daily market brief schedule set for 6:30 AM and 7:00 AM ET")

def run_scheduler():
    """Run the scheduler continuously"""
    setup_schedule()
    
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    # For testing - send immediately
    print("Sending test daily brief...")
    send_daily_brief() 