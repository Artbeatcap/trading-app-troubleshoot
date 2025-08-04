#!/usr/bin/env python3
"""
Newsletter Scheduler Runner
Run this script to start the automated daily newsletter sending
"""
import os
import sys
import logging
from datetime import datetime

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('newsletter_scheduler.log'),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

def main():
    """Main function to run the newsletter scheduler"""
    logger.info("🚀 Starting Newsletter Scheduler")
    logger.info(f"Started at: {datetime.now()}")
    
    try:
        # Import and run the scheduler
        from tasks import run_scheduler
        run_scheduler()
    except KeyboardInterrupt:
        logger.info("📴 Newsletter scheduler stopped by user")
    except Exception as e:
        logger.error(f"❌ Newsletter scheduler error: {str(e)}")
        raise

if __name__ == "__main__":
    main() 