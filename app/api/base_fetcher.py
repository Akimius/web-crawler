"""
Base API Fetcher - Abstract base class for API-based news fetchers.

Unlike BaseCrawler which scrapes HTML, this class fetches
structured data from REST APIs.
"""

import logging
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional, Callable

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class BaseAPIFetcher(ABC):
    """Abstract base class for API-based news fetchers."""

    def __init__(
        self,
        api_key: str,
        request_delay: float = 0.5,
        timeout: int = 30,
        max_retries: int = 3,
        start_date: str = None,
        end_date: str = None,
        **kwargs
    ):
        """
        Initialize the API fetcher.

        Args:
            api_key: API key for authentication
            request_delay: Seconds to wait between requests
            timeout: HTTP request timeout in seconds
            max_retries: Maximum retry attempts for failed requests
            start_date: Start date for filtering (YYYY-MM-DD)
            end_date: End date for filtering (YYYY-MM-DD)
        """
        if not api_key:
            raise ValueError("API key is required")

        self.api_key = api_key
        self.request_delay = request_delay
        self.timeout = timeout
        self.max_retries = max_retries
        self.start_date = start_date
        self.end_date = end_date

        self._last_request_time = 0
        self._session = self._create_session()

    def _create_session(self) -> requests.Session:
        """Create a requests session with retry logic."""
        session = requests.Session()

        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _rate_limit(self):
        """Implement rate limiting between requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.request_delay:
            sleep_time = self.request_delay - elapsed
            logger.debug(f"Rate limiting: sleeping {sleep_time:.2f}s")
            time.sleep(sleep_time)
        self._last_request_time = time.time()

    def _get_headers(self) -> Dict[str, str]:
        """Get default headers for API requests. Override in subclasses."""
        return {}

    def _make_request(
        self,
        url: str,
        params: Dict[str, Any] = None,
        headers: Dict[str, str] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Make an HTTP GET request to the API.

        Args:
            url: The API endpoint URL
            params: Query parameters
            headers: Additional headers

        Returns:
            JSON response as dict, or None on error
        """
        self._rate_limit()

        request_headers = self._get_headers()
        if headers:
            request_headers.update(headers)

        try:
            response = self._session.get(
                url,
                params=params,
                headers=request_headers,
                timeout=self.timeout
            )

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                logger.error("API authentication failed: Invalid API key")
                raise ValueError("Invalid API key")
            elif response.status_code == 429:
                logger.warning("Rate limit exceeded, backing off...")
                time.sleep(60)  # Wait 60 seconds on rate limit
                return None
            else:
                logger.error(
                    f"API request failed: {response.status_code} - {response.text}"
                )
                return None

        except requests.exceptions.Timeout:
            logger.error(f"Request timeout for {url}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error: {e}")
            return None

    @abstractmethod
    def fetch_articles(
        self,
        page: int = 1,
        page_size: int = 10
    ) -> Dict[str, Any]:
        """
        Fetch a single page of articles from the API.

        Args:
            page: Page number to fetch
            page_size: Number of articles per page

        Returns:
            Dict with keys: articles (List), total_results (int), status (str)
        """
        pass

    @abstractmethod
    def fetch_all_articles(
        self,
        max_pages: int = 10,
        page_size: int = 10,
        on_batch: Callable[[List[Dict[str, Any]]], None] = None
    ) -> List[Dict[str, Any]]:
        """
        Fetch all articles with pagination support.

        Args:
            max_pages: Maximum number of pages to fetch
            page_size: Articles per page
            on_batch: Optional callback for batch processing

        Returns:
            List of all articles (empty list if on_batch provided)
        """
        pass

    def close(self):
        """Clean up resources."""
        if self._session:
            self._session.close()
            self._session = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        return False
