"""
Task scheduler for automated daily market brief sending
"""
import schedule
import time
import logging
from datetime import datetime, date
import pytz
from market_brief_generator import send_market_brief_to_subscribers

logger = logging.getLogger(__name__)

# Track last send date (ET) to prevent duplicates in case of restarts
last_sent_date_et: date | None = None
eastern_tz = pytz.timezone("America/New_York")


def send_daily_brief():
    """Send the daily market brief to all confirmed subscribers once per day (ET)."""
    global last_sent_date_et
    try:
        today_et = datetime.now(eastern_tz).date()
        if last_sent_date_et == today_et:
            logger.info("Daily brief already sent today (ET). Skipping duplicate send.")
            return 0

        logger.info("Starting scheduled daily brief sending (08:00 ET)")
        success_count = send_market_brief_to_subscribers()
        last_sent_date_et = today_et
        logger.info(f"Daily brief sent to {success_count} subscribers")
        return success_count
    except Exception as e:
        logger.error(f"Error in scheduled daily brief: {str(e)}")
        return 0


def check_and_send_daily():
    """Trigger send precisely at 08:00 America/New_York regardless of server timezone."""
    now_et = datetime.now(eastern_tz)
    if now_et.hour == 8 and now_et.minute == 0:
        send_daily_brief()


def setup_schedule():
    """Setup a minute-level scheduler and gate to 08:00 ET inside the task."""
    schedule.every().minute.do(check_and_send_daily)
    logger.info("Daily market brief schedule set to check every minute; will send at 8:00 AM ET only")


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