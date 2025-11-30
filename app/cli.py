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
from dotenv import load_dotenv

# Add app directory to path
sys.path.insert(0, str(Path(__file__).parent))

from models.database import Database, Article, Source

# Load environment variables
load_dotenv()


def list_sources(db: Database):
    """List all news sources"""
    source_model = Source(db)
    sources = source_model.get_all_active()
    
    if not sources:
        print("No sources found.")
        return
    
    print(f"\n{'ID':<5} {'Name':<30} {'Articles':<10} {'Last Crawled':<20}")
    print("="*70)
    
    article_model = Article(db)
    for source in sources:
        count = article_model.count_by_source(source['id'])
        last_crawled = source['last_crawled'] or 'Never'
        print(f"{source['id']:<5} {source['name']:<30} {count:<10} {last_crawled:<20}")
    
    print()


def list_articles(db: Database, limit: int = 20, source_id: int = None):
    """List recent articles"""
    article_model = Article(db)
    
    if source_id:
        articles = article_model.get_by_source(source_id, limit=limit)
    else:
        articles = article_model.get_latest(limit=limit)
    
    if not articles:
        print("No articles found.")
        return
    
    print(f"\nShowing {len(articles)} most recent articles:\n")
    
    for idx, article in enumerate(articles, 1):
        source_name = article.get('source_name', 'Unknown')
        published = article['published_date'] or 'Unknown date'
        
        print(f"{idx}. [{source_name}] {article['title']}")
        print(f"   Published: {published}")
        print(f"   URL: {article['url']}")
        print(f"   Summary: {article['summary'][:100]}...")
        print()


def search_articles(db: Database, keyword: str, limit: int = 20):
    """Search articles by keyword"""
    with db.get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT a.*, s.name as source_name
            FROM articles a
            JOIN sources s ON a.source_id = s.id
            WHERE a.title LIKE ? OR a.content LIKE ?
            ORDER BY a.published_date DESC
            LIMIT ?
        ''', (f'%{keyword}%', f'%{keyword}%', limit))
        
        articles = [dict(row) for row in cursor.fetchall()]
    
    if not articles:
        print(f"No articles found matching '{keyword}'.")
        return
    
    print(f"\nFound {len(articles)} articles matching '{keyword}':\n")
    
    for idx, article in enumerate(articles, 1):
        source_name = article.get('source_name', 'Unknown')
        published = article['published_date'] or 'Unknown date'
        
        print(f"{idx}. [{source_name}] {article['title']}")
        print(f"   Published: {published}")
        print(f"   URL: {article['url']}")
        print()


def show_stats(db: Database):
    """Show database statistics"""
    article_model = Article(db)
    source_model = Source(db)
    
    sources = source_model.get_all_active()
    
    with db.get_connection() as conn:
        cursor = conn.cursor()
        
        # Total articles
        cursor.execute('SELECT COUNT(*) as count FROM articles')
        total_articles = cursor.fetchone()['count']
        
        # Articles today
        today = datetime.now().date().isoformat()
        cursor.execute('SELECT COUNT(*) as count FROM articles WHERE DATE(scraped_date) = ?', (today,))
        articles_today = cursor.fetchone()['count']
        
        # Articles this week
        week_ago = (datetime.now() - timedelta(days=7)).date().isoformat()
        cursor.execute('SELECT COUNT(*) as count FROM articles WHERE DATE(scraped_date) >= ?', (week_ago,))
        articles_week = cursor.fetchone()['count']
    
    print("\n" + "="*60)
    print("Database Statistics")
    print("="*60)
    print(f"Total sources: {len(sources)}")
    print(f"Total articles: {total_articles}")
    print(f"Articles scraped today: {articles_today}")
    print(f"Articles scraped this week: {articles_week}")
    print("="*60)
    
    print("\nArticles by source:")
    for source in sources:
        count = article_model.count_by_source(source['id'])
        print(f"  {source['name']}: {count}")
    print()


def main():
    """Main CLI function"""
    parser = argparse.ArgumentParser(description='News Crawler Database CLI')
    parser.add_argument('--db', default=os.getenv('DB_PATH', 'data/news.db'),
                       help='Database path')
    
    subparsers = parser.add_subparsers(dest='command', help='Command to run')
    
    # Sources command
    subparsers.add_parser('sources', help='List all news sources')
    
    # Articles command
    articles_parser = subparsers.add_parser('articles', help='List recent articles')
    articles_parser.add_argument('--limit', type=int, default=20, help='Number of articles to show')
    articles_parser.add_argument('--source', type=int, help='Filter by source ID')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search articles')
    search_parser.add_argument('keyword', help='Keyword to search for')
    search_parser.add_argument('--limit', type=int, default=20, help='Number of results')
    
    # Stats command
    subparsers.add_parser('stats', help='Show database statistics')
    
    args = parser.parse_args()
    
    # Check if database exists
    if not Path(args.db).exists():
        print(f"Error: Database not found at {args.db}")
        print("Run the crawler first to create the database.")
        sys.exit(1)
    
    # Initialize database
    db = Database(args.db)
    
    # Execute command
    if args.command == 'sources':
        list_sources(db)
    elif args.command == 'articles':
        list_articles(db, limit=args.limit, source_id=args.source)
    elif args.command == 'search':
        search_articles(db, args.keyword, limit=args.limit)
    elif args.command == 'stats':
        show_stats(db)
    else:
        parser.print_help()


if __name__ == '__main__':
    main()
