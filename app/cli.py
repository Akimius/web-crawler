#!/usr/bin/env python3
"""
News Crawler - Database Query CLI

Simple command-line tool to query the news database.
"""

import os
import sys
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, Any, Callable, Optional

from dotenv import load_dotenv

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from models.database import Database, Article, Source

# Load environment variables
load_dotenv()

# Constants
DEFAULT_LIMIT = 20
SEPARATOR_WIDTH = 60


def _print_article(idx: int, article: Dict[str, Any]) -> None:
    """Print a single article in a formatted way."""
    source_name = article.get('source_name', 'Unknown')
    published = article['published_date'] or 'Unknown date'
    print(f"{idx}. [{source_name}] {article['title']}")
    print(f"   Published: {published}")
    print(f"   URL: {article['url']}")
    print()


def _print_articles(articles: list[Dict[str, Any]], header: str) -> None:
    """Print a list of articles with a header."""
    if not articles:
        print("No articles found.")
        return

    print(f"\n{header}\n")
    for idx, article in enumerate(articles, 1):
        _print_article(idx, article)


def _format_date_range(start_date: Optional[str], end_date: Optional[str]) -> str:
    """Format date range for display."""
    if not start_date and not end_date:
        return ""
    return f" (from {start_date or 'any'} to {end_date or 'any'})"


def cmd_sources(db: Database, args: argparse.Namespace) -> None:
    """List all news sources."""
    source_model = Source(db)
    sources = source_model.get_all_active()

    if not sources:
        print("No sources found.")
        return

    print(f"\n{'ID':<5} {'Name':<30} {'Articles':<10} {'Last Crawled':<20}")
    print("=" * 70)

    article_model = Article(db)
    for source in sources:
        count = article_model.count_by_source(source['id'])
        last_crawled = source['last_crawled'] or 'Never'
        print(f"{source['id']:<5} {source['name']:<30} {count:<10} {last_crawled:<20}")

    print()


def cmd_articles(db: Database, args: argparse.Namespace) -> None:
    """List recent articles."""
    article_model = Article(db)

    if args.source:
        articles = article_model.get_by_source(args.source, limit=args.limit)
    else:
        articles = article_model.get_latest(limit=args.limit)

    _print_articles(articles, f"Showing {len(articles)} most recent articles:")


def cmd_search(db: Database, args: argparse.Namespace) -> None:
    """Search articles by keyword with optional date range."""
    article_model = Article(db)
    articles = article_model.search(
        args.keyword,
        limit=args.limit,
        start_date=args.start_date,
        end_date=args.end_date
    )

    date_range = _format_date_range(args.start_date, args.end_date)

    if not articles:
        print(f"No articles found matching '{args.keyword}'{date_range}.")
        return

    _print_articles(articles, f"Found {len(articles)} articles matching '{args.keyword}'{date_range}:")


def cmd_stats(db: Database, args: argparse.Namespace) -> None:
    """Show database statistics."""
    article_model = Article(db)
    source_model = Source(db)

    sources = source_model.get_all_active()
    today = datetime.now().date().isoformat()
    week_ago = (datetime.now() - timedelta(days=7)).date().isoformat()

    total_articles = article_model.count_total()
    articles_today = article_model.count_scraped_on_date(today)
    articles_week = article_model.count_scraped_since(week_ago)

    print("\n" + "=" * SEPARATOR_WIDTH)
    print("Database Statistics")
    print("=" * SEPARATOR_WIDTH)
    print(f"Total sources: {len(sources)}")
    print(f"Total articles: {total_articles}")
    print(f"Articles scraped today: {articles_today}")
    print(f"Articles scraped this week: {articles_week}")
    print("=" * SEPARATOR_WIDTH)

    print("\nArticles by source:")
    for source in sources:
        count = article_model.count_by_source(source['id'])
        print(f"  {source['name']}: {count}")
    print()


# Command registry
COMMANDS: Dict[str, Callable[[Database, argparse.Namespace], None]] = {
    'sources': cmd_sources,
    'articles': cmd_articles,
    'search': cmd_search,
    'stats': cmd_stats,
}


def setup_parser() -> argparse.ArgumentParser:
    """Set up argument parser with all subcommands."""
    parser = argparse.ArgumentParser(description='News Crawler Database CLI')
    parser.add_argument(
        '--db',
        default=os.getenv('DB_PATH', 'data/news.db'),
        help='Database path'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    # Sources command
    subparsers.add_parser('sources', help='List all news sources')

    # Articles command
    articles_parser = subparsers.add_parser('articles', help='List recent articles')
    articles_parser.add_argument(
        '--limit', type=int, default=DEFAULT_LIMIT,
        help='Number of articles to show'
    )
    articles_parser.add_argument('--source', type=int, help='Filter by source ID')

    # Search command
    search_parser = subparsers.add_parser('search', help='Search articles')
    search_parser.add_argument('keyword', help='Keyword to search for')
    search_parser.add_argument(
        '--limit', type=int, default=DEFAULT_LIMIT,
        help='Number of results'
    )
    search_parser.add_argument(
        '--from', dest='start_date',
        help='Start date (YYYY-MM-DD format)'
    )
    search_parser.add_argument(
        '--to', dest='end_date',
        help='End date (YYYY-MM-DD format)'
    )

    # Stats command
    subparsers.add_parser('stats', help='Show database statistics')

    return parser


def main() -> None:
    """Main CLI entry point."""
    parser = setup_parser()
    args = parser.parse_args()

    # Check if database exists
    db_path = Path(args.db)
    if not db_path.exists():
        print(f"Error: Database not found at {args.db}")
        print("Run the crawler first to create the database.")
        sys.exit(1)

    # Initialize database
    try:
        db = Database(args.db)
    except Exception as e:
        print(f"Error: Failed to connect to database: {e}")
        sys.exit(1)

    # Execute command
    if args.command in COMMANDS:
        try:
            COMMANDS[args.command](db, args)
        except Exception as e:
            print(f"Error: Command failed: {e}")
            sys.exit(1)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()