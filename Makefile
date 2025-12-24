.PHONY: help setup build crawl crawl-date crawl-range newsapi newsapi-range newsapi-full start stop restart logs clean stats sources articles search

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

setup: ## Initialize project structure
	./setup.sh

clean: ## Remove database and logs, CSV-files
	rm -rf data/*.db data/*.csv data/export/*.csv data/*.db-journal logs/*.log

build: ## Build Docker image
	docker compose build

crawl: ## Run one-time crawl (today's articles)
	docker compose run --rm crawler python main.py

crawl-date: ## Crawl specific date (use date=YYYY-MM-DD)
	@if [ -z "$(date)" ]; then \
		echo "Usage: make crawl-date date=2024-11-15"; \
	else \
		docker compose run --rm crawler python main.py --from $(date) --to $(date); \
	fi

crawl-range: ## Crawl range: dates (from=YYYY-MM-DD) or pages (from=1 to=100)
	@if [ -z "$(from)" ]; then \
		echo "Usage: make crawl-range from=2024-11-01 to=2024-11-30  # date range"; \
		echo "       make crawl-range from=1 to=100                  # page range"; \
	else \
		docker compose run --rm crawler python main.py --from $(from) --to $(or $(to),$(from)); \
	fi

newsapi: ## Fetch gold news from NewsAPI (today's articles)
	docker compose run --rm crawler python main.py --source newsapi

newsapi-range: ## Fetch NewsAPI with date range (from=YYYY-MM-DD to=YYYY-MM-DD)
	@if [ -z "$(from)" ]; then \
		echo "Usage: make newsapi-range from=2025-12-01 to=2025-12-24"; \
	else \
		docker compose run --rm crawler python main.py --source newsapi --from $(from) --to $(or $(to),$(from)); \
	fi

newsapi-full: ## Fetch NewsAPI with full article content (from=YYYY-MM-DD to=YYYY-MM-DD)
	@if [ -z "$(from)" ]; then \
		echo "Usage: make newsapi-full from=2025-12-01 to=2025-12-24"; \
		echo "This fetches full article content from each URL (slower)"; \
	else \
		docker compose run --rm crawler python main.py --source newsapi --from $(from) --to $(or $(to),$(from)) --fetch-content; \
	fi

stop: ## Stop scheduled crawler
	docker compose down

restart: ## Restart scheduled crawler
	docker compose restart

logs: ## View crawler logs
	docker compose logs -f crawler

stats: ## Show database statistics
	docker compose run --rm crawler python cli.py stats

sources: ## List all news sources
	docker compose run --rm crawler python cli.py sources

articles: ## List recent articles (use limit=N to customize)
	docker compose run --rm crawler python cli.py articles --limit $(or $(limit),20)

search: ## Search articles (use keyword=word, limit=N, from=date, to=date)
	@if [ -z "$(keyword)" ]; then \
		echo "Usage: make search keyword=your_keyword [limit=N] [from=YYYY-MM-DD] [to=YYYY-MM-DD]"; \
	else \
		docker compose run --rm crawler python cli.py search --keyword "$(keyword)" \
			$(if $(limit),--limit $(limit)) \
			$(if $(from),--from $(from)) \
			$(if $(to),--to $(to)); \
	fi

shell: ## Open bash shell in container
	docker compose run --rm crawler bash

db: ## Open SQLite database shell
	sqlite3 data/news.db

rebuild: ## Rebuild and restart everything
	docker compose down
	docker compose build
	docker compose up -d
