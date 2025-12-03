# Quick Start Guide

## 5-Minute Setup

### 1. Setup Project Structure
```bash
./setup.sh
```

### 2. Build Docker Image
```bash
docker-compose build
```

### 3. Run First Crawl
```bash
docker compose run --rm crawler python main.py
```

This will:
- Create SQLite database in `data/news.db`
- Initialize 3 news sources ( Ukrayinska Pravda)
- Crawl and save articles
- Show statistics

### 4. Query Your Data
```bash
# View statistics
docker-compose run --rm crawler python cli.py stats

# List recent articles
docker-compose run --rm crawler python cli.py articles --limit 10

# Search for articles
docker compose run --rm crawler python cli.py search "technology"
```

### 5. (Optional) Setup Scheduled Crawling
Edit `docker-compose.yml` and uncomment the scheduler command:
```yaml
command: python scheduler.py
```

Then start:
```bash
docker-compose up -d
```

## What's Next?

### Customize Crawl Schedule
Edit `.env`:
```env
# Run every 6 hours
CRAWL_SCHEDULE=0 */6 * * *

# Run daily at midnight
CRAWL_SCHEDULE=0 0 * * *

# Run every hour
CRAWL_SCHEDULE=0 * * * *
```

### Add More News Sources
See README.md section "Adding New News Sources"

### Adjust Rate Limiting
Edit `.env`:
```env
REQUEST_DELAY=2    # 2 seconds between requests (be nice to servers!)
```

### View Logs
```bash
# Container logs
docker-compose logs -f

# Log file
tail -f logs/crawler.log
```

## Common Commands Cheat Sheet

```bash
# One-time crawl
docker-compose run --rm crawler python main.py

# Start scheduler
docker-compose up -d

# Stop scheduler
docker-compose down

# View logs
docker-compose logs -f

# List sources
docker-compose run --rm crawler python cli.py sources

# Recent articles
docker-compose run --rm crawler python cli.py articles

# Search
docker-compose run --rm crawler python cli.py search "keyword"

# Stats
docker-compose run --rm crawler python cli.py stats

# Database shell
sqlite3 data/news.db

# Rebuild after changes
docker-compose build
```

## Troubleshooting

### Database locked error
```bash
# Stop all containers
docker-compose down

# Try again
docker-compose run --rm crawler python main.py
```

### No articles found
- Check if the news sites changed their HTML structure
- View logs for specific errors: `docker-compose logs -f`
- Try with lower `REQUEST_DELAY` or higher `TIMEOUT` in `.env`

### Permission errors on data/logs
```bash
chmod -R 777 data logs
```
