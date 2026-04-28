"""Task scheduler for automated daily market brief sending.

The scheduler is restart-safe: the last-sent date (in America/New_York) is
persisted to ``artifacts/brief_state/daily_last_sent_et.txt`` so that if the
process restarts mid-day we don't re-send the brief. A separate weekly state
file is maintained (for weekly jobs) to keep daily/weekly freshness tracking
independent.
"""
from __future__ import annotations

import logging
import time
from datetime import date, datetime
from pathlib import Path
from typing import Optional

import pytz
import schedule

from market_brief_generator import send_market_brief_to_subscribers

logger = logging.getLogger(__name__)

eastern_tz = pytz.timezone("America/New_York")

# ---------------------------------------------------------------------------
# Persistent last-sent tracking (ET, one file per cadence)
# ---------------------------------------------------------------------------

_STATE_DIR = Path("artifacts") / "brief_state"
DAILY_STATE_FILE = _STATE_DIR / "daily_last_sent_et.txt"
WEEKLY_STATE_FILE = _STATE_DIR / "weekly_last_sent_et.txt"


def _load_last_sent(path: Path) -> Optional[date]:
    try:
        raw = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    except Exception:
        logger.exception("Could not read last-sent state file %s", path)
        return None
    if not raw:
        return None
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        logger.warning("Ignoring malformed last-sent state in %s: %r", path, raw)
        return None


def _save_last_sent(path: Path, value: date) -> None:
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(value.strftime("%Y-%m-%d"), encoding="utf-8")
    except Exception:
        logger.exception("Could not persist last-sent state to %s", path)


# In-memory cache; seeded from disk lazily
last_sent_date_et: Optional[date] = None


def _get_last_sent_daily() -> Optional[date]:
    global last_sent_date_et
    if last_sent_date_et is None:
        last_sent_date_et = _load_last_sent(DAILY_STATE_FILE)
    return last_sent_date_et


def _mark_daily_sent(today_et: date) -> None:
    global last_sent_date_et
    last_sent_date_et = today_et
    _save_last_sent(DAILY_STATE_FILE, today_et)


def mark_weekly_sent(today_et: Optional[date] = None) -> None:
    """Public hook so the weekly sender can record its last-run date."""
    today_et = today_et or datetime.now(eastern_tz).date()
    _save_last_sent(WEEKLY_STATE_FILE, today_et)


def get_last_daily_sent() -> Optional[date]:
    return _load_last_sent(DAILY_STATE_FILE)


def get_last_weekly_sent() -> Optional[date]:
    return _load_last_sent(WEEKLY_STATE_FILE)


# ---------------------------------------------------------------------------
# Scheduler entry points
# ---------------------------------------------------------------------------


def send_daily_brief():
    """Send the daily market brief to all confirmed subscribers once per day (ET)."""
    try:
        today_et = datetime.now(eastern_tz).date()
        if _get_last_sent_daily() == today_et:
            logger.info("Daily brief already sent today (ET). Skipping duplicate send.")
            return 0

        logger.info("Starting scheduled daily brief sending (08:00 ET)")
        success_count = send_market_brief_to_subscribers()
        _mark_daily_sent(today_et)
        logger.info(f"Daily brief sent to {success_count} subscribers")
        return success_count
    except Exception as e:
        logger.error(f"Error in scheduled daily brief: {str(e)}")
        return 0


def check_and_send_daily():
    """Send at or after 08:00 ET on weekdays, once per day (prevents misses)."""
    now_et = datetime.now(eastern_tz)

    if now_et.weekday() > 4:
        return

    today_et = now_et.date()

    if _get_last_sent_daily() == today_et:
        return

    if (now_et.hour > 8) or (now_et.hour == 8 and now_et.minute >= 0):
        send_daily_brief()


def setup_schedule():
    """Setup a minute-level scheduler and gate to >= 08:00 ET on weekdays inside the task."""
    schedule.every().minute.do(check_and_send_daily)
    logger.info("Daily brief checks every minute; sends once after 8:00 AM ET Mon-Fri")


def run_scheduler():
    """Run the scheduler continuously"""
    setup_schedule()
    while True:
        schedule.run_pending()
        time.sleep(60)


if __name__ == "__main__":
    logger.info("Starting market brief scheduler...")
    run_scheduler()
