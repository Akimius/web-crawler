#!/usr/bin/env python3
"""
News Crawler - Main Entry Point

This script initializes the database, sets up sources, and runs the crawler.
"""

import os
import sys
import logging
import argparse
from pathlib import Path
from dotenv import load_dotenv

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from utils.logging_config import setup_logging
from utils.crawler_manager import CrawlerManager

# Load environment variables
load_dotenv()

logger = logging.getLogger(__name__)

def init_sources(manager: CrawlerManager):
    """Initialize default news sources"""
    # Get today's date for RBC Ukraine archive
    from datetime import datetime
    today = datetime.now().strftime('%Y-%m-%d')

    sources = [
        # {
        #     'name': 'BBC News',
        #     'url': 'https://www.bbc.com/news',
        #     'parser_class': 'BBCNewsCrawler'
        # },
        # {
        #     'name': 'The Guardian',
        #     'url': 'https://www.theguardian.com/international',
        #     'parser_class': 'GuardianNewsCrawler'
        # },
        # {
        #     'name': 'Ukrayinska Pravda',
        #     'url': 'https://www.pravda.com.ua/news/',
        #     'parser_class': 'UkrPravdaCrawler'
        # },
        {
            'name': 'РБК-Україна',
            'url': f'https://www.rbc.ua/ukr/archive/{today.replace("-", "/")}',
            'parser_class': 'RBCUkraineCrawler'
        }
    ]
    
    for source in sources:
        try:
            manager.add_source(
                name=source['name'],
                url=source['url'],
                parser_class=source['parser_class']
            )
        except Exception as e:
            logger.error(f"Failed to add source {source['name']}: {e}")


def main():
    """Main execution function"""
    # Setup argument parser
    parser = argparse.ArgumentParser(
        description='News Crawler - Scrape news articles from configured sources',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  # Crawl today's articles (default)
  python main.py

  # Crawl specific date
  python main.py --from 2024-11-15 --to 2024-11-15

  # Crawl date range
  python main.py --from 2024-11-01 --to 2024-11-30

  # Crawl from date to today
  python main.py --from 2024-11-01
        '''
    )

    parser.add_argument(
        '--from',
        dest='start_date',
        type=str,
        help='Start date for crawling (format: YYYY-MM-DD). Defaults to today.'
    )

    parser.add_argument(
        '--to',
        dest='end_date',
        type=str,
        help='End date for crawling (format: YYYY-MM-DD). Defaults to today.'
    )

    args = parser.parse_args()

    # Get configuration from environment
    db_path = os.getenv('DB_PATH', 'data/news.db')
    log_level = os.getenv('LOG_LEVEL', 'INFO')
    log_file = os.getenv('LOG_FILE', 'logs/crawler.log')
    user_agent = os.getenv('USER_AGENT')
    request_delay = float(os.getenv('REQUEST_DELAY', 1.0))
    timeout = int(os.getenv('TIMEOUT', 30))

    # CLI arguments override environment variables
    start_date = args.start_date  # Format: YYYY-MM-DD
    end_date = args.end_date      # Format: YYYY-MM-DD

    # Setup logging
    setup_logging(log_level=log_level, log_file=log_file)

    logger.info("="*60)
    logger.info("News Crawler Starting")
    logger.info("="*60)

    # Log date filtering if configured
    if start_date or end_date:
        date_range = f"from {start_date or 'any'} to {end_date or 'any'}"
        logger.info(f"Date filtering enabled: {date_range}")

    # Ensure data directory exists
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)

    # Initialize crawler manager
    manager = CrawlerManager(
        db_path=db_path,
        user_agent=user_agent,
        request_delay=request_delay,
        timeout=timeout,
        start_date=start_date,
        end_date=end_date
    )
    
    # Initialize sources
    logger.info("Initializing news sources...")
    init_sources(manager)
    
    # List available sources
    sources = manager.list_sources()
    logger.info(f"Active sources: {len(sources)}")
    for source in sources:
        logger.info(f"  - {source['name']} ({source['url']})")
    
    # Available parsers
    parsers = CrawlerManager.get_available_parsers()
    logger.info(f"Available parsers: {', '.join(parsers)}")
    
    # Run crawler
    logger.info("Starting crawl...")
    stats = manager.crawl_all_sources()
    
    # Display results
    logger.info("="*60)
    logger.info("Crawl Summary")
    logger.info("="*60)
    logger.info(f"Sources crawled: {stats['sources_crawled']}")
    logger.info(f"Articles found: {stats['articles_found']}")
    logger.info(f"Articles saved: {stats['articles_saved']}")
    logger.info(f"Articles skipped: {stats['articles_skipped']}")
    logger.info(f"Errors: {stats['errors']}")
    logger.info("="*60)
    
    if stats['errors'] > 0:
        logger.warning(f"Crawl completed with {stats['errors']} errors")
        sys.exit(1)
    else:
        logger.info("Crawl completed successfully")
        sys.exit(0)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Crawler interrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        sys.exit(1)
