"""
API Module - API-based news fetchers.

This module provides fetchers for retrieving news from REST APIs,
as opposed to web scraping.
"""

from api.base_fetcher import BaseAPIFetcher
from api.newsapi_fetcher import NewsAPIFetcher

__all__ = ["BaseAPIFetcher", "NewsAPIFetcher"]
