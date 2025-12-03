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
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from models.database import Database, Article, Source

load_dotenv()


class Formatter:
    """Handles formatting of CLI output."""

    SEPARATOR = "=" * 70

    @staticmethod
    def print_header(title: str) -> None:
        print(f"\n{Formatter.SEPARATOR}")
        print(title)
        print(Formatter.SEPARATOR)

    @staticmethod
    def print_article(article: Dict[str, Any], index: int) -> None:
        source_name = article.get('source_name', 'Unknown')
        published = article.get('published_date') or 'Unknown date'
        print(f"{index}. [{source_name}] {article['title']}")
        print(f"   Published: {published}")
        print(f"   URL: {article['url']}")
        print()

    @staticmethod
    def print_articles(articles: List[Dict[str, Any]], header: str) -> None:
        if not articles:
            print("No articles found.")
            return
        print(f"\n{header}\n")
        for idx, article in enumerate(articles, 1):
            Formatter.print_article(article, idx)

    @staticmethod
    def print_sources_table(sources: List[Dict[str, Any]], counts: Dict[int, int]) -> None:
        if not sources:
            print("No sources found.")
            return
        print(f"\n{'ID':<5} {'Name':<30} {'Articles':<10} {'Last Crawled':<20}")
        print(Formatter.SEPARATOR)
        for source in sources:
            count = counts.get(source['id'], 0)
            last_crawled = source['last_crawled'] or 'Never'
            print(f"{source['id']:<5} {source['name']:<30} {count:<10} {last_crawled:<20}")
        print()


class ArticleRepository:
    """Extended article queries not in the base model."""

    def __init__(self, db: Database):
        self.db = db
        self.article_model = Article(db)

    def search(
        self,
        keyword: str,
        limit: int = 20,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """Search articles by keyword with optional date range."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            query = '''
                SELECT a.*, s.name as source_name
                FROM articles a
                JOIN sources s ON a.source_id = s.id
                WHERE (a.title LIKE ? OR a.content LIKE ?)
            '''
            params: List[Any] = [f'%{keyword}%', f'%{keyword}%']

            if start_date and end_date:
                query += ' AND a.published_date BETWEEN ? AND ?'
                params.extend([start_date, end_date])
            elif start_date:
                query += ' AND a.published_date >= ?'
                params.append(start_date)
            elif end_date:
                query += ' AND a.published_date <= ?'
                params.append(end_date)

            query += ' ORDER BY a.published_date DESC LIMIT ?'
            params.append(limit)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_stats(self) -> Dict[str, int]:
        """Get article statistics."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute('SELECT COUNT(*) as count FROM articles')
            total = cursor.fetchone()['count']

            today = datetime.now().date().isoformat()
            cursor.execute(
                'SELECT COUNT(*) as count FROM articles WHERE DATE(scraped_date) = ?',
                (today,)
            )
            today_count = cursor.fetchone()['count']

            week_ago = (datetime.now() - timedelta(days=7)).date().isoformat()
            cursor.execute(
                'SELECT COUNT(*) as count FROM articles WHERE DATE(scraped_date) >= ?',
                (week_ago,)
            )
            week_count = cursor.fetchone()['count']

            return {
                'total': total,
                'today': today_count,
                'week': week_count,
            }


class CLI:
    """Command-line interface for the news crawler database."""

    def __init__(self, db_path: str):
        self.db = Database(db_path)
        self.source_model = Source(self.db)
        self.article_model = Article(self.db)
        self.article_repo = ArticleRepository(self.db)

    def list_sources(self) -> None:
        """List all news sources."""
        sources = self.source_model.get_all_active()
        counts = {s['id']: self.article_model.count_by_source(s['id']) for s in sources}
        Formatter.print_sources_table(sources, counts)

    def list_articles(self, limit: int = 20, source_id: Optional[int] = None) -> None:
        """List recent articles."""
        if source_id:
            articles = self.article_model.get_by_source(source_id, limit=limit)
            # Add source_name for consistency
            source = self.source_model.get_by_id(source_id)
            source_name = source['name'] if source else 'Unknown'
            for article in articles:
                article['source_name'] = source_name
        else:
            articles = self.article_model.get_latest(limit=limit)

        Formatter.print_articles(articles, f"Showing {len(articles)} most recent articles:")

    def search_articles(
        self,
        keyword: str,
        limit: int = 20,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> None:
        """Search articles by keyword with optional date range."""
        articles = self.article_repo.search(keyword, limit, start_date, end_date)

        date_info = ""
        if start_date or end_date:
            date_info = f" (from {start_date or 'any'} to {end_date or 'any'})"

        if not articles:
            print(f"No articles found matching '{keyword}'{date_info}.")
            return

        Formatter.print_articles(articles, f"Found {len(articles)} articles matching '{keyword}'{date_info}:")

    def show_stats(self) -> None:
        """Show database statistics."""
        sources = self.source_model.get_all_active()
        stats = self.article_repo.get_stats()

        Formatter.print_header("Database Statistics")
        print(f"Total sources: {len(sources)}")
        print(f"Total articles: {stats['total']}")
        print(f"Articles scraped today: {stats['today']}")
        print(f"Articles scraped this week: {stats['week']}")
        print(Formatter.SEPARATOR)

        print("\nArticles by source:")
        for source in sources:
            count = self.article_model.count_by_source(source['id'])
            print(f"  {source['name']}: {count}")
        print()


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser."""
    parser = argparse.ArgumentParser(description='News Crawler Database CLI')
    parser.add_argument(
        '--db',
        default=os.getenv('DB_PATH', 'data/news.db'),
        help='Database path'
    )

    subparsers = parser.add_subparsers(dest='command', help='Command to run')

    subparsers.add_parser('sources', help='List all news sources')

    articles_parser = subparsers.add_parser('articles', help='List recent articles')
    articles_parser.add_argument('--limit', type=int, default=20, help='Number of articles to show')
    articles_parser.add_argument('--source', type=int, help='Filter by source ID')

    search_parser = subparsers.add_parser('search', help='Search articles')
    search_parser.add_argument('keyword', help='Keyword to search for')
    search_parser.add_argument('--limit', type=int, default=20, help='Number of results')
    search_parser.add_argument('--from', dest='start_date', help='Start date (YYYY-MM-DD format)')
    search_parser.add_argument('--to', dest='end_date', help='End date (YYYY-MM-DD format)')

    subparsers.add_parser('stats', help='Show database statistics')

    return parser


def main() -> None:
    """Main CLI entry point."""
    parser = build_parser()
    args = parser.parse_args()

    if not Path(args.db).exists():
        print(f"Error: Database not found at {args.db}")
        print("Run the crawler first to create the database.")
        sys.exit(1)

    cli = CLI(args.db)

    commands = {
        'sources': cli.list_sources,
        'articles': lambda: cli.list_articles(limit=args.limit, source_id=args.source),
        'search': lambda: cli.search_articles(
            args.keyword,
            limit=args.limit,
            start_date=args.start_date,
            end_date=args.end_date
        ),
        'stats': cli.show_stats,
    }

    handler = commands.get(args.command)
    if handler:
        handler()
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
