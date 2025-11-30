#!/usr/bin/env python3
"""
News Crawler Scheduler

Runs the crawler on a schedule using APScheduler.
"""

import os
import sys
import logging
from pathlib import Path
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.logging_config import setup_logging
from utils.crawler_manager import CrawlerManager
from main import init_sources

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)


def run_crawl():
    """Execute a single crawl"""
    try:
        logger.info("Scheduled crawl starting...")
        
        # Get configuration
        db_path = os.getenv('DB_PATH', 'data/news.db')
        user_agent = os.getenv('USER_AGENT')
        request_delay = float(os.getenv('REQUEST_DELAY', 1.0))
        timeout = int(os.getenv('TIMEOUT', 30))
        
        # Initialize manager
        manager = CrawlerManager(
            db_path=db_path,
            user_agent=user_agent,
            request_delay=request_delay,
            timeout=timeout
        )
        
        # Run crawl
        stats = manager.crawl_all_sources()
        
        logger.info(f"Scheduled crawl complete: {stats}")
        
    except Exception as e:
        logger.error(f"Error during scheduled crawl: {e}", exc_info=True)


def main():
    """Main scheduler function"""
    # Get configuration
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    log_file = os.getenv('LOG_FILE', 'logs/crawler.log')
    crawl_schedule = os.getenv('CRAWL_SCHEDULE', '0 */6 * * *')  # Default: every 6 hours
    
    # Setup logging
    setup_logging(log_level=log_level, log_file=log_file)
    
    logger.info("="*60)
    logger.info("News Crawler Scheduler Starting")
    logger.info("="*60)
    logger.info(f"Schedule: {crawl_schedule}")
    
    # Initialize database and sources
    db_path = os.getenv('DB_PATH', 'data/news.db')
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    
    manager = CrawlerManager(db_path=db_path)
    init_sources(manager)
    
    # Create scheduler
    scheduler = BlockingScheduler()
    
    # Add crawl job
    try:
        # Parse cron schedule
        # Format: minute hour day month day_of_week
        parts = crawl_schedule.split()
        if len(parts) != 5:
            raise ValueError(f"Invalid cron schedule: {crawl_schedule}")
        
        trigger = CronTrigger(
            minute=parts[0],
            hour=parts[1],
            day=parts[2],
            month=parts[3],
            day_of_week=parts[4]
        )
        
        scheduler.add_job(
            run_crawl,
            trigger=trigger,
            id='news_crawler',
            name='News Crawler',
            max_instances=1,  # Prevent overlapping runs
            replace_existing=True
        )
        
        logger.info("Scheduler configured successfully")
        logger.info("Waiting for scheduled crawls...")
        
        # Run once immediately on startup
        logger.info("Running initial crawl...")
        run_crawl()
        
        # Start scheduler
        scheduler.start()
        
    except (KeyboardInterrupt, SystemExit):
        logger.info("Scheduler stopped by user")
        scheduler.shutdown()
        sys.exit(0)
    except Exception as e:
        logger.error(f"Scheduler error: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
