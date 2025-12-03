bb# News Crawler

A Docker-based Python web crawler for parsing news sites and storing articles in SQLite database.

## Features

- Crawl multiple news sources
- Parse article content, dates, and metadata
- Store data in SQLite database
- Scheduled crawling support
- Configurable via environment variables
- Dockerized for easy deployment

## Project Structure

```
.
├── app/
│   ├── models/          # Database models
│   ├── parsers/         # Site-specific parsers
│   ├── scrapers/        # Crawler logic
│   ├── utils/           # Helper functions
│   ├── main.py          # Entry point
│   └── scheduler.py     # Scheduled tasks
├── data/                # SQLite database
├── logs/                # Application logs
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── .env
```

## Setup

1. **Initialize project structure:**
   ```bash
   ./setup.sh
   ```

2. **Configure environment:**
   Edit `.env` file with your settings:
   - Add news source URLs
   - Set crawl schedule
   - Configure database path

3. **Build Docker image:**
   ```bash
   docker-compose build
   ```

4. **Run crawler:**
   
   One-time crawl:
   ```bash
   docker-compose run --rm crawler python main.py
   ```
   
   Scheduled crawling:
   ```bash
   docker-compose up -d
   ```

## Usage

### One-Time Manual Crawl
```bash
docker-compose run --rm crawler python main.py
```

### Scheduled Crawling (Background)
```bash
# Start scheduler in background
docker-compose up -d

# View logs
docker-compose logs -f crawler

# Stop scheduler
docker-compose down
```

### Query Database with CLI

List all sources:
```bash
docker-compose run --rm crawler python cli.py sources
```

View recent articles:
```bash
docker-compose run --rm crawler python cli.py articles --limit 10
```

Search articles by keyword:
```bash
docker-compose run --rm crawler python cli.py search "Ukraine"
```

Show statistics:
```bash
docker-compose run --rm crawler python cli.py stats
```

### Direct Database Access
```bash
sqlite3 data/news.db
```

Example queries:
```sql
-- Recent articles
SELECT title, published_date FROM articles ORDER BY published_date DESC LIMIT 10;

-- Articles by source
SELECT s.name, COUNT(*) FROM articles a 
JOIN sources s ON a.source_id = s.id 
GROUP BY s.name;
```

## Configuration

Edit `.env` file:
```env
# Database
DB_PATH=data/news.db

# Logging
LOG_LEVEL=INFO
LOG_FILE=logs/crawler.log

# Crawler settings
USER_AGENT=Mozilla/5.0...
REQUEST_DELAY=1        # Seconds between requests
TIMEOUT=30             # Request timeout
MAX_RETRIES=3          # Max retry attempts

# Scheduling (cron format: minute hour day month day_of_week)
CRAWL_SCHEDULE=0 */6 * * *  # Every 6 hours
```

## Adding New News Sources

### Method 1: Modify main.py
Edit `app/main.py` and add to the `init_sources()` function:
```python
{
    'name': 'Your News Site',
    'url': 'https://example.com/news',
    'parser_class': 'YourNewsCrawler'
}
```

### Method 2: Create Custom Parser

1. Create parser in `app/parsers/your_parser.py`:
```python
from app.scrapers.base_crawler import BaseCrawler

class YourNewsCrawler(BaseCrawler):
    def __init__(self, **kwargs):
        super().__init__(
            source_url='https://example.com/news',
            **kwargs
        )
    
    def get_article_urls(self) -> List[str]:
        # Implement article URL extraction
        pass
    
    def parse_article(self, url: str) -> Optional[Dict[str, Any]]:
        # Implement article parsing
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

## Development

### Enter Container
```bash
docker-compose run --rm crawler bash
```

### Run Tests Locally
```bash
# Install dependencies
pip install -r requirements.txt

# Run crawler
python app/main.py
```

### Debug Single Source
```bash
docker-compose run --rm crawler python -c "
from utils.crawler_manager import CrawlerManager
manager = CrawlerManager('data/news.db')
stats = manager.crawl_source(1)  # Crawl source ID 1
print(stats)
"
```

## Database Schema

### sources table
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

### articles table
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

## Available Parsers

- **BBCNewsCrawler** - BBC News (https://www.bbc.com/news)
- **GuardianNewsCrawler** - The Guardian (https://www.theguardian.com/international)
- **UkrPravdaCrawler** - Ukrayinska Pravda (https://www.pravda.com.ua/news/)

## License

MIT
