"""
NewsAPI Fetcher - Fetches gold price news from NewsAPI.

This module provides a client for the NewsAPI /everything endpoint
to fetch articles about gold prices, bullion, and precious metals.
"""

import os
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional, Callable

from api.base_fetcher import BaseAPIFetcher

logger = logging.getLogger(__name__)


class NewsAPIFetcher(BaseAPIFetcher):
    """Fetcher for NewsAPI gold price news."""

    BASE_URL = "https://newsapi.org/v2/everything"
    DEFAULT_QUERY = "gold+price+OR+bullion+OR+precious+metals"

    def __init__(
        self,
        api_key: str = None,
        query: str = None,
        language: str = "en",
        sort_by: str = "publishedAt",
        page_size: int = None,
        max_pages: int = None,
        **kwargs
    ):
        """
        Initialize the NewsAPI fetcher.

        Args:
            api_key: NewsAPI key (defaults to NEWSAPI_KEY env var)
            query: Search query (defaults to gold price query)
            language: Article language filter
            sort_by: Sort order (publishedAt, relevancy, popularity)
            page_size: Articles per page (defaults to NEWSAPI_PAGE_SIZE or 10)
            max_pages: Max pages to fetch (defaults to NEWSAPI_MAX_PAGES or 10)
            **kwargs: Additional args passed to BaseAPIFetcher
        """
        # Get API key from environment if not provided
        api_key = api_key or os.getenv("NEWSAPI_KEY")
        if not api_key:
            raise ValueError(
                "NewsAPI key required. Set NEWSAPI_KEY environment variable."
            )

        super().__init__(api_key=api_key, **kwargs)

        self.query = query or self.DEFAULT_QUERY
        self.language = language
        self.sort_by = sort_by
        self.page_size = page_size or int(os.getenv("NEWSAPI_PAGE_SIZE", 10))
        self.max_pages = max_pages or int(os.getenv("NEWSAPI_MAX_PAGES", 10))

    def _get_headers(self) -> Dict[str, str]:
        """Get headers with API key."""
        return {
            "X-Api-Key": self.api_key,
            "Accept": "application/json"
        }

    def _build_params(self, page: int, page_size: int) -> Dict[str, Any]:
        """Build query parameters for the API request."""
        params = {
            "q": self.query,
            "language": self.language,
            "sortBy": self.sort_by,
            "pageSize": page_size,
            "page": page
        }

        if self.start_date:
            params["from"] = self.start_date
        if self.end_date:
            params["to"] = self.end_date

        return params

    def _parse_published_date(self, iso_date: str) -> Optional[str]:
        """Convert ISO 8601 date to YYYY-MM-DD format."""
        if not iso_date:
            return None
        try:
            # Handle ISO 8601 format: 2025-12-01T12:00:00Z
            dt = datetime.fromisoformat(iso_date.replace("Z", "+00:00"))
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            logger.warning(f"Invalid date format: {iso_date}")
            return None

    def _transform_article(self, raw: Dict[str, Any]) -> Dict[str, Any]:
        """
        Transform NewsAPI article format to internal format.

        NewsAPI format:
        {
            "source": {"id": "...", "name": "..."},
            "author": "...",
            "title": "...",
            "description": "...",
            "url": "...",
            "urlToImage": "...",
            "publishedAt": "2025-12-01T12:00:00Z",
            "content": "..."
        }

        Internal format:
        {
            "title": "...",
            "content": "...",
            "author": "...",
            "published_date": "2025-12-01",
            "summary": "...",
            "url": "..."
        }
        """
        return {
            "title": raw.get("title", ""),
            "content": raw.get("content") or raw.get("description", ""),
            "author": raw.get("author", ""),
            "published_date": self._parse_published_date(raw.get("publishedAt")),
            "summary": raw.get("description", ""),
            "url": raw.get("url", "")
        }

    def fetch_articles(
        self,
        page: int = 1,
        page_size: int = None
    ) -> Dict[str, Any]:
        """
        Fetch a single page of articles from NewsAPI.

        Args:
            page: Page number to fetch (1-indexed)
            page_size: Number of articles per page

        Returns:
            Dict with keys:
                - status: "ok" or "error"
                - articles: List of transformed articles
                - total_results: Total number of available articles
                - message: Error message if status is "error"
        """
        page_size = page_size or self.page_size
        params = self._build_params(page, page_size)

        logger.info(f"Fetching NewsAPI page {page} (size={page_size})")
        logger.debug(f"Query params: {params}")

        response = self._make_request(self.BASE_URL, params=params)

        if response is None:
            return {
                "status": "error",
                "articles": [],
                "total_results": 0,
                "message": "Request failed"
            }

        status = response.get("status", "error")

        if status != "ok":
            error_msg = response.get("message", "Unknown error")
            logger.error(f"NewsAPI error: {error_msg}")
            return {
                "status": "error",
                "articles": [],
                "total_results": 0,
                "message": error_msg
            }

        raw_articles = response.get("articles", [])
        total_results = response.get("totalResults", 0)

        # Transform articles to internal format
        articles = []
        for raw in raw_articles:
            try:
                article = self._transform_article(raw)
                # Skip articles without title or URL
                if article.get("title") and article.get("url"):
                    articles.append(article)
            except Exception as e:
                logger.warning(f"Failed to transform article: {e}")
                continue

        logger.info(f"Fetched {len(articles)} articles (total available: {total_results})")

        return {
            "status": "ok",
            "articles": articles,
            "total_results": total_results
        }

    def fetch_all_articles(
        self,
        max_pages: int = None,
        page_size: int = None,
        on_batch: Callable[[List[Dict[str, Any]]], None] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all articles across multiple pages.

        Args:
            max_pages: Maximum number of pages to fetch
            page_size: Articles per page
            on_batch: Optional callback invoked after each page with articles list

        Returns:
            List of all articles if on_batch is None, otherwise empty list
        """
        max_pages = max_pages or self.max_pages
        page_size = page_size or self.page_size
        all_articles = []

        logger.info(f"Starting NewsAPI fetch: max_pages={max_pages}, page_size={page_size}")

        for page in range(1, max_pages + 1):
            result = self.fetch_articles(page=page, page_size=page_size)

            if result["status"] != "ok":
                logger.error(f"API error on page {page}: {result.get('message')}")
                break

            articles = result["articles"]

            if not articles:
                logger.info(f"No more articles at page {page}")
                break

            if on_batch:
                on_batch(articles)
            else:
                all_articles.extend(articles)

            # Check if we've fetched all available articles
            total_results = result.get("total_results", 0)
            fetched_so_far = page * page_size
            if fetched_so_far >= total_results:
                logger.info(f"Fetched all {total_results} available articles")
                break

        total_fetched = len(all_articles) if not on_batch else "N/A (batch mode)"
        logger.info(f"NewsAPI fetch complete: {total_fetched} articles")

        return all_articles if not on_batch else []

    def fetch_and_store(
        self,
        storage,
        source_id: int,
        source_name: str,
        max_pages: int = None,
        page_size: int = None
    ) -> Dict[str, int]:
        """
        Fetch articles and store them using the provided storage manager.

        Args:
            storage: StorageManager instance
            source_id: Database source ID
            source_name: Source name for logging
            max_pages: Maximum pages to fetch
            page_size: Articles per page

        Returns:
            Dict with keys: found, saved, skipped
        """
        stats = {"found": 0, "saved": 0, "skipped": 0}

        def save_batch(articles_batch):
            stats["found"] += len(articles_batch)
            result = storage.create_article_batch(
                source_id=source_id,
                source_name=source_name,
                articles=articles_batch,
                batch_size=len(articles_batch)
            )
            stats["saved"] += result["saved"]
            stats["skipped"] += result["skipped"]

        self.fetch_all_articles(
            max_pages=max_pages,
            page_size=page_size,
            on_batch=save_batch
        )

        logger.info(
            f"NewsAPI storage complete: {stats['saved']} saved, "
            f"{stats['skipped']} skipped out of {stats['found']} found"
        )

        return stats
