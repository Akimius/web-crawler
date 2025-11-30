.PHONY: help setup build crawl start stop restart logs clean stats sources articles search

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

setup: ## Initialize project structure
	./setup.sh

build: ## Build Docker image
	docker-compose build

crawl: ## Run one-time crawl
	docker-compose run --rm crawler python main.py

start: ## Start scheduled crawler in background
	docker-compose up -d

stop: ## Stop scheduled crawler
	docker-compose down

restart: ## Restart scheduled crawler
	docker-compose restart

logs: ## View crawler logs
	docker-compose logs -f crawler

clean: ## Remove database and logs
	rm -rf data/*.db data/*.db-journal logs/*.log

stats: ## Show database statistics
	docker-compose run --rm crawler python cli.py stats

sources: ## List all news sources
	docker-compose run --rm crawler python cli.py sources

articles: ## List recent articles (use LIMIT=N to customize)
	docker-compose run --rm crawler python cli.py articles --limit $(or $(LIMIT),20)

search: ## Search articles (use KEYWORD=word)
	@if [ -z "$(KEYWORD)" ]; then \
		echo "Usage: make search KEYWORD=your_keyword"; \
	else \
		docker-compose run --rm crawler python cli.py search "$(KEYWORD)"; \
	fi

shell: ## Open bash shell in container
	docker-compose run --rm crawler bash

db: ## Open SQLite database shell
	sqlite3 data/news.db

test: ## Run a test crawl (same as crawl)
	docker-compose run --rm crawler python main.py

rebuild: ## Rebuild and restart everything
	docker-compose down
	docker-compose build
	docker-compose up -d
