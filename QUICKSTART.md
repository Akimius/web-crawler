# Quick Start Guide

## 5-Minute Setup

### 1. Setup Project Structure
```bash
./setup.sh
```

### 2. Build Docker Image
```bash
docker compose build
```

### 3. Run First Crawl
```bash
docker compose run --rm crawler python main.py --from="2025-12-03" --to="2025-12-03"
python3 app/main.py --from="2025-12-03" --to="2025-12-03"
```
local setup

This will:
- Create SQLite database in `data/news.db`
- Initialize 3 news sources (BBC, Guardian, Ukrayinska Pravda)
- Crawl and save articles
- Show statistics

### 4. Query Your Data
```bash
# View statistics
docker compose run --rm crawler python cli.py stats

# List recent articles
docker compose run --rm crawler python cli.py articles --limit 10

# Search for articles
docker compose run --rm crawler python cli.py search "technology"
```

Then start:
```bash
docker compose up -d
```

## What's Next?

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
docker compose logs -f

# Log file
tail -f logs/crawler.log
```

## Common Commands Cheat Sheet

```bash
# One-time crawl
docker compose run --rm crawler python main.py

# Start scheduler
docker compose up -d

# Stop scheduler
docker compose down

# View logs
docker compose logs -f

# List sources
docker compose run --rm crawler python cli.py sources

# Recent articles
docker compose run --rm crawler python cli.py articles

# Search
docker compose run --rm crawler python cli.py search --keyword "term"
docker compose run --rm crawler python cli.py search -k "term"

# With other options
docker compose run --rm crawler python cli.py search -k "term" --from 2024-01-01 --to 2024-12-31
  
# Stats
docker compose run --rm crawler python cli.py stats

# Database shell
sqlite3 data/news.db

# Rebuild after changes
docker compose build
```

## Troubleshooting

### Database locked error
```bash
# Stop all containers
docker compose down

# Try again
docker compose run --rm crawler python main.py
```

### No articles found
- Check if the news sites changed their HTML structure
- View logs for specific errors: `docker compose logs -f`
- Try with lower `REQUEST_DELAY` or higher `TIMEOUT` in `.env`

### Permission errors on data/logs
```bash
chmod -R 777 data logs
```
