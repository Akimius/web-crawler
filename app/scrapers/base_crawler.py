import logging
import time
import requests
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

logger = logging.getLogger(__name__)


class BaseCrawler(ABC):
    """Base crawler class with common functionality"""
    
    def __init__(self, source_url: str, user_agent: str = None, 
                 request_delay: float = 1.0, timeout: int = 30, max_retries: int = 3):
        self.source_url = source_url
        self.base_domain = urlparse(source_url).netloc
        self.request_delay = request_delay
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Setup session with retries
        self.session = self._create_session(user_agent or self._get_default_user_agent())
        
        # Track last request time for rate limiting
        self.last_request_time = 0
    
    def _get_default_user_agent(self) -> str:
        """Get default user agent"""
        return 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    
    def _create_session(self, user_agent: str) -> requests.Session:
        """Create requests session with retry logic"""
        session = requests.Session()
        
        # Configure retries
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        # Set headers
        session.headers.update({
            'User-Agent': user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
        })
        
        return session
    
    def _rate_limit(self):
        """Implement rate limiting between requests"""
        elapsed = time.time() - self.last_request_time
        if elapsed < self.request_delay:
            time.sleep(self.request_delay - elapsed)
        self.last_request_time = time.time()
    
    def fetch_page(self, url: str) -> Optional[str]:
        """Fetch a page and return HTML content"""
        self._rate_limit()
        
        try:
            logger.info(f"Fetching: {url}")
            response = self.session.get(url, timeout=self.timeout)
            response.raise_for_status()
            
            return response.text
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None
    
    def parse_html(self, html: str) -> BeautifulSoup:
        """Parse HTML content with BeautifulSoup"""
        return BeautifulSoup(html, 'lxml')
    
    def absolute_url(self, url: str) -> str:
        """Convert relative URL to absolute"""
        return urljoin(self.source_url, url)
    
    def is_valid_url(self, url: str) -> bool:
        """Check if URL is valid and belongs to the source domain"""
        try:
            parsed = urlparse(url)
            return bool(parsed.netloc) and bool(parsed.scheme)
        except Exception:
            return False
    
    def extract_text(self, soup: BeautifulSoup, selector: str, 
                     default: str = '', strip: bool = True) -> str:
        """Extract text from element using CSS selector"""
        element = soup.select_one(selector)
        if element:
            text = element.get_text(strip=strip)
            return text if text else default
        return default
    
    def extract_attribute(self, soup: BeautifulSoup, selector: str, 
                         attribute: str, default: str = '') -> str:
        """Extract attribute from element using CSS selector"""
        element = soup.select_one(selector)
        if element:
            return element.get(attribute, default)
        return default
    
    @abstractmethod
    def get_article_urls(self) -> List[str]:
        """
        Get list of article URLs from the source.
        Must be implemented by subclasses.
        """
        pass
    
    @abstractmethod
    def parse_article(self, url: str) -> Optional[Dict[str, Any]]:
        """
        Parse a single article and return structured data.
        Must be implemented by subclasses.
        
        Returns:
            Dictionary with keys: title, content, author, published_date, summary
        """
        pass
    
    def crawl(self) -> List[Dict[str, Any]]:
        """
        Main crawl method that orchestrates the crawling process.
        Returns list of parsed articles.
        """
        logger.info(f"Starting crawl for: {self.source_url}")
        
        # Get article URLs
        article_urls = self.get_article_urls()
        logger.info(f"Found {len(article_urls)} article URLs")
        
        # Parse each article
        articles = []
        for idx, url in enumerate(article_urls, 1):
            logger.info(f"Processing article {idx}/{len(article_urls)}: {url}")
            
            article_data = self.parse_article(url)
            if article_data:
                article_data['url'] = url
                articles.append(article_data)
            else:
                logger.warning(f"Failed to parse article: {url}")
        
        logger.info(f"Successfully parsed {len(articles)}/{len(article_urls)} articles")
        return articles
    
    def close(self):
        """Clean up resources"""
        if self.session:
            self.session.close()
    
    def __enter__(self):
        """Context manager entry"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit"""
        self.close()


class GenericNewsCrawler(BaseCrawler):
    """Generic news crawler with common patterns"""
    
    def __init__(self, source_url: str, config: Dict[str, Any], **kwargs):
        """
        Initialize with configuration for selectors
        
        config should contain:
        - article_list_selector: CSS selector for article links on homepage
        - article_title_selector: CSS selector for article title
        - article_content_selector: CSS selector for article content
        - article_author_selector: CSS selector for author (optional)
        - article_date_selector: CSS selector for published date (optional)
        - article_date_attribute: Attribute containing date (optional)
        """
        super().__init__(source_url, **kwargs)
        self.config = config
    
    def get_article_urls(self) -> List[str]:
        """Get article URLs from homepage using configured selector"""
        html = self.fetch_page(self.source_url)
        if not html:
            return []
        
        soup = self.parse_html(html)
        article_links = soup.select(self.config.get('article_list_selector', 'a'))
        
        urls = []
        for link in article_links:
            href = link.get('href')
            if href:
                absolute = self.absolute_url(href)
                if self.is_valid_url(absolute):
                    urls.append(absolute)
        
        # Remove duplicates while preserving order
        return list(dict.fromkeys(urls))
    
    def parse_article(self, url: str) -> Optional[Dict[str, Any]]:
        """Parse article using configured selectors"""
        html = self.fetch_page(url)
        if not html:
            return None
        
        soup = self.parse_html(html)
        
        # Extract title
        title = self.extract_text(
            soup, 
            self.config.get('article_title_selector', 'h1')
        )
        
        if not title:
            logger.warning(f"No title found for: {url}")
            return None
        
        # Extract content
        content = self.extract_text(
            soup,
            self.config.get('article_content_selector', 'article')
        )
        
        # Extract author (optional)
        author = None
        if 'article_author_selector' in self.config:
            author = self.extract_text(soup, self.config['article_author_selector'])
        
        # Extract published date (optional)
        published_date = None
        if 'article_date_selector' in self.config:
            if 'article_date_attribute' in self.config:
                published_date = self.extract_attribute(
                    soup,
                    self.config['article_date_selector'],
                    self.config['article_date_attribute']
                )
            else:
                published_date = self.extract_text(
                    soup,
                    self.config['article_date_selector']
                )
        
        # Generate summary (first 200 chars of content)
        summary = content[:200] + '...' if len(content) > 200 else content
        
        return {
            'title': title,
            'content': content,
            'author': author,
            'published_date': published_date,
            'summary': summary
        }
