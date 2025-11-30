# News Crawler - Configuration & Setup Guide

This document provides comprehensive configuration and setup instructions for the News Crawler project.

## Project Overview

A Docker-based Python web crawler that parses news sites and stores articles in a SQLite database. The crawler supports scheduled crawling, multiple news sources, and includes built-in parsers for BBC News, The Guardian, and Ukrayinska Pravda.

## Prerequisites

- Docker 20.10+
- Docker Compose 1.29+
- 100MB+ disk space
- Internet connection

## Quick Start

```bash
# 1. Initialize project structure
./setup.sh

# 2. Build Docker image
docker compose build

# 3. Run first crawl
docker compose run --rm crawler python main.py

# 4. View statistics
docker compose run --rm crawler python cli.py stats
```

Or using Makefile:
```bash
make build
make crawl
make stats
```

## Configuration

### Environment Variables (.env)

The `.env` file controls all crawler behavior. Copy from `.env.example` and customize:

#### Database Configuration
```env
DB_PATH=data/news.db
```
- **DB_PATH**: Path to SQLite database file
- Default: `data/news.db`
- Must be within a mounted Docker volume

#### Logging Configuration
```env
LOG_LEVEL=INFO
LOG_FILE=logs/crawler.log
```
- **LOG_LEVEL**: Logging verbosity (DEBUG, INFO, WARNING, ERROR)
- **LOG_FILE**: Path to log file
- Logs are also printed to stdout

#### Crawler Settings
```env
USER_AGENT=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
REQUEST_DELAY=1
TIMEOUT=30
MAX_RETRIES=3
```
- **USER_AGENT**: Browser user agent string for HTTP requests
- **REQUEST_DELAY**: Seconds to wait between requests (rate limiting)
- **TIMEOUT**: HTTP request timeout in seconds
- **MAX_RETRIES**: Maximum retry attempts for failed requests

#### Scheduling Configuration
```env
CRAWL_SCHEDULE=0 */6 * * *
```
- **CRAWL_SCHEDULE**: Cron format schedule (minute hour day month day_of_week)
- Default: `0 */6 * * *` (every 6 hours)
- Examples:
  - `0 */6 * * *` - Every 6 hours
  - `0 0 * * *` - Daily at midnight
  - `0 */3 * * *` - Every 3 hours
  - `*/30 * * * *` - Every 30 minutes

#### News Sources (Optional)
```env
NEWS_SOURCES=https://example.com,https://another-news.com
```
- Comma-separated list of news URLs
- Note: Sources are primarily managed in `app/main.py`

## Project Structure

```
crawler/
├── app/
│   ├── models/          # Database models (SQLite)
│   ├── parsers/         # Site-specific parsers
│   ├── scrapers/        # Crawler logic
│   ├── utils/           # Helper functions
│   ├── main.py          # Entry point for one-time crawls
│   ├── scheduler.py     # Scheduled task runner
│   └── cli.py           # CLI for querying database
├── data/                # SQLite database storage
│   └── news.db          # Created automatically
├── logs/                # Application logs
│   └── crawler.log      # Created automatically
├── .env                 # Configuration (create from .env.example)
├── docker compose.yml   # Docker orchestration
├── Dockerfile           # Container definition
├── requirements.txt     # Python dependencies
├── Makefile             # Convenience commands
└── setup.sh             # Initialization script
```

## Common Operations

### One-Time Crawl
```bash
# Using Docker Compose
docker compose run --rm crawler python main.py

# Using Makefile
make crawl
```

### Scheduled Crawling (Background)
```bash
# Start scheduler
docker compose up -d

# View logs
docker compose logs -f crawler

# Stop scheduler
docker compose down
```

### Database Queries

#### Using CLI Tool
```bash
# View statistics
docker compose run --rm crawler python cli.py stats

# List all sources
docker compose run --rm crawler python cli.py sources

# View recent articles
docker compose run --rm crawler python cli.py articles --limit 10

# Search articles
docker compose run --rm crawler python cli.py search "keyword"
```

#### Direct SQLite Access
```bash
# Open database shell
sqlite3 data/news.db

# Or using Makefile
make db
```

Common SQL queries:
```sql
-- Recent articles
SELECT title, published_date FROM articles ORDER BY published_date DESC LIMIT 10;

-- Articles by source
SELECT s.name, COUNT(*) FROM articles a
JOIN sources s ON a.source_id = s.id
GROUP BY s.name;

-- Full-text search
SELECT title, url FROM articles WHERE content LIKE '%keyword%';
```

### Makefile Commands

```bash
make help       # Show all available commands
make build      # Build Docker image
make crawl      # Run one-time crawl
make start      # Start scheduled crawler (background)
make stop       # Stop crawler
make logs       # View crawler logs
make stats      # Show database statistics
make sources    # List all news sources
make articles   # Show recent articles (LIMIT=10)
make search     # Search articles (KEYWORD="term")
make db         # Open SQLite shell
make clean      # Remove containers and volumes
```

## Adding News Sources

### Available Parsers
- `BBCNewsCrawler` - BBC News
- `GuardianNewsCrawler` - The Guardian
- `UkrPravdaCrawler` - Ukrayinska Pravda

### Method 1: Add to Existing Sources

Edit `app/main.py` and add to `init_sources()`:
```python
{
    'name': 'Your News Site',
    'url': 'https://example.com/news',
    'parser_class': 'BBCNewsCrawler'  # Reuse existing parser
}
```

### Method 2: Create Custom Parser

1. Create `app/parsers/your_parser.py`:
```python
from app.scrapers.base_crawler import BaseCrawler
from typing import List, Optional, Dict, Any

class YourNewsCrawler(BaseCrawler):
    def __init__(self, **kwargs):
        super().__init__(
            source_url='https://example.com/news',
            **kwargs
        )

    def get_article_urls(self) -> List[str]:
        """Extract article URLs from news feed"""
        # Implementation
        pass

    def parse_article(self, url: str) -> Optional[Dict[str, Any]]:
        """Parse individual article"""
        # Return dict with: title, content, author, published_date
        pass
```

2. Register in `app/utils/crawler_manager.py`:
```python
from app.parsers.your_parser import YourNewsCrawler

PARSERS = {
    'YourNewsCrawler': YourNewsCrawler,
    # ... other parsers
}
```

3. Add source in `app/main.py`

## Database Schema

### sources Table
```sql
CREATE TABLE sources (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    parser_class TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    last_crawled TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
```

### articles Table
```sql
CREATE TABLE articles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id INTEGER NOT NULL,
    url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    content TEXT,
    summary TEXT,
    author TEXT,
    published_date TEXT,
    scraped_date TEXT NOT NULL,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    FOREIGN KEY (source_id) REFERENCES sources (id)
);
```

## Development

### Local Development (Without Docker)
```bash
# Install dependencies
pip install -r requirements.txt

# Run crawler
python app/main.py

# Run CLI
python app/cli.py stats
```

### Enter Container for Debugging
```bash
docker compose run --rm crawler bash
```

### Debug Single Source
```bash
docker compose run --rm crawler python -c "
from utils.crawler_manager import CrawlerManager
manager = CrawlerManager('data/news.db')
stats = manager.crawl_source(1)  # Crawl source ID 1
print(stats)
"
```

## Troubleshooting

### Database Locked Error
```bash
# Stop all containers
docker compose down

# Retry operation
make crawl
```

### Permission Errors
```bash
# Fix directory permissions
chmod 777 data logs
```

### No Articles Found
1. Check internet connection
2. Verify news source is accessible
3. Increase `TIMEOUT` in `.env`
4. Check logs: `tail -f logs/crawler.log`
5. Some sites may block automated requests

### Parser Errors
- Check if website structure has changed
- Update parser selectors in `app/parsers/`
- Test with single source first

### Docker Issues
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install docker.io docker compose

# macOS (Homebrew)
brew install --cask docker
```

## Dependencies

Key Python packages (see `requirements.txt`):
- `beautifulsoup4` - HTML parsing
- `requests` - HTTP client
- `scrapy` - Web crawling framework
- `newspaper3k` - Article extraction
- `APScheduler` - Task scheduling
- `python-dotenv` - Environment variable management

## Performance Tuning

### Crawl Speed
- Decrease `REQUEST_DELAY` (minimum: 0.5s recommended)
- Increase `TIMEOUT` for slow sites
- Reduce `MAX_RETRIES` for faster failures

### Resource Usage
- Docker container uses ~256MB RAM
- Database grows ~1MB per 100 articles
- Logs rotate automatically (configure in code)

### Scheduling Optimization
- Avoid peak traffic hours
- Distribute sources across multiple schedules
- Consider time zones for international sources

## Security Considerations

1. **User Agent**: Update `USER_AGENT` to identify your crawler
2. **Rate Limiting**: Respect `REQUEST_DELAY` to avoid overwhelming servers
3. **robots.txt**: Check site policies before crawling
4. **Data Privacy**: Be mindful of storing personal information
5. **Environment**: Don't commit `.env` file with sensitive data

## File Locations

| File | Path | Purpose |
|------|------|---------|
| Database | `data/news.db` | SQLite database |
| Logs | `logs/crawler.log` | Application logs |
| Config | `.env` | Environment configuration |
| Source Code | `app/` | Python application |
| Entry Point | `app/main.py` | One-time crawl |
| Scheduler | `app/scheduler.py` | Scheduled crawls |
| CLI | `app/cli.py` | Database queries |

## Next Steps

1. Customize crawl schedule in `.env`
2. Add additional news sources
3. Build a web frontend for the database
4. Export data as JSON/CSV
5. Implement data analysis or visualization
6. Set up monitoring and alerts

## Resources

- README.md - General documentation
- INSTALL.md - Installation instructions
- QUICKSTART.md - Quick start guide
- PROJECT_SUMMARY.md - Project overview
