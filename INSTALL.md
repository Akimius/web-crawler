# Installation Instructions

## Extract and Run

### 1. Extract the Project
```bash
tar xzf news-crawler.tar.gz
cd news-crawler
```

### 2. Initialize Structure
```bash
chmod +x setup.sh
./setup.sh
```

This creates:
- `app/` directory structure
- `data/` for SQLite database
- `logs/` for application logs
- `.env` file (copy of .env.example)

### 3. Configure (Optional)
Edit `.env` file to customize:
```bash
nano .env
```

Important settings:
- `REQUEST_DELAY` - Seconds between requests (default: 1)
- `CRAWL_SCHEDULE` - Cron schedule for periodic crawling
- `LOG_LEVEL` - DEBUG, INFO, WARNING, ERROR

### 4. Build Docker Image
```bash
docker-compose build
```

This will:
- Pull Python 3.11-slim base image
- Install system dependencies
- Install Python packages from requirements.txt
- Setup working directory

### 5. Run First Crawl
```bash
docker-compose run --rm crawler python main.py
```

Expected output:
```
News Crawler Starting
============================================================
Initializing news sources...
Active sources: 3
  - BBC News (https://www.bbc.com/news)
  - The Guardian (https://www.theguardian.com/international)
  - Ukrayinska Pravda (https://www.pravda.com.ua/news/)
Available parsers: BBCNewsCrawler, GuardianNewsCrawler, UkrPravdaCrawler
Starting crawl...
...
Crawl Summary
============================================================
Sources crawled: 3
Articles found: 60
Articles saved: 60
Articles skipped: 0
Errors: 0
============================================================
```

### 6. Query Your Data
```bash
# View statistics
docker-compose run --rm crawler python cli.py stats

# List sources
docker-compose run --rm crawler python cli.py sources

# View recent articles
docker-compose run --rm crawler python cli.py articles --limit 10
```

## Using Makefile (Recommended)

The Makefile provides shortcuts for common tasks:

```bash
# View all available commands
make help

# Build
make build

# Run one-time crawl
make crawl

# View statistics
make stats

# List sources
make sources

# View articles
make articles LIMIT=20

# Search
make search KEYWORD="Ukraine"
```

## Setup Scheduled Crawling

### Option 1: Docker Compose (Recommended)

Edit `docker-compose.yml` and uncomment:
```yaml
command: python scheduler.py
```

Then start:
```bash
docker-compose up -d
```

View logs:
```bash
docker-compose logs -f
```

Stop:
```bash
docker-compose down
```

### Option 2: Cron (Host System)

Add to crontab:
```bash
0 */6 * * * cd /path/to/news-crawler && docker-compose run --rm crawler python main.py >> logs/cron.log 2>&1
```

## Troubleshooting

### Docker not installed?
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install docker.io docker-compose

# macOS (Homebrew)
brew install --cask docker
```

### Permission denied on setup.sh?
```bash
chmod +x setup.sh
```

### Database locked error?
```bash
# Stop all containers
docker-compose down

# Try again
make crawl
```

### Can't access database file?
```bash
# Fix permissions
chmod 777 data logs
```

### No articles found?
- Check internet connection
- Some news sites may block automated requests
- Try increasing `TIMEOUT` in `.env`
- Check logs: `cat logs/crawler.log`

## What's Next?

1. **Customize crawl schedule** - Edit `CRAWL_SCHEDULE` in `.env`
2. **Add more sources** - See README.md "Adding New News Sources"
3. **Build a frontend** - Use the SQLite database with your web framework
4. **Export data** - Query database and export as JSON/CSV

## Quick Reference

```bash
# Build
make build

# One-time crawl
make crawl

# Start scheduler (background)
make start

# Stop scheduler
make stop

# View logs
make logs

# Statistics
make stats

# Database shell
make db

# Help
make help
```

## System Requirements

- **Docker**: 20.10+
- **Docker Compose**: 1.29+
- **Disk Space**: 100MB + article data
- **RAM**: 256MB minimum
- **Network**: Internet connection required

## File Locations

- **Database**: `data/news.db`
- **Logs**: `logs/crawler.log`
- **Config**: `.env`
- **Code**: `app/`

## Support

Check the logs first:
```bash
tail -f logs/crawler.log
```

Common issues:
1. Database locked → Stop containers: `docker-compose down`
2. No articles → Check logs for specific errors
3. Permission errors → `chmod 777 data logs`

Happy crawling! 🚀
