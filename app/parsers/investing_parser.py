import logging
from typing import List, Dict, Any, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from scrapers.base_crawler import BaseCrawler

logger = logging.getLogger(__name__)


class InvestingCrawler(BaseCrawler):
    """Investing.com Gold News crawler using Selenium for JS-rendered content"""

    def __init__(self, **kwargs):
        super().__init__(
            source_url='https://www.investing.com/commodities/gold-news/12',
            **kwargs
        )
        self._driver = None

    def _get_driver(self):
        """Lazy initialization of Selenium driver"""
        if self._driver is None:
            from browser import get_chrome_driver
            self._driver = get_chrome_driver()
            logger.info("Selenium driver initialized for Investing.com")
        return self._driver

    def get_article_urls(self) -> List[str]:
        """Get article URLs from Investing.com gold news page using Selenium"""
        driver = self._get_driver()
        urls = []

        try:
            logger.info(f"Fetching: {self.source_url}")
            driver.get(self.source_url)

            wait = WebDriverWait(driver, 10)
            wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'ul[data-test="news-list"]'))
            )

            links = driver.find_elements(By.CSS_SELECTOR, 'a[data-test="article-title-link"]')

            for link in links:
                url = link.get_attribute("href")
                if url and self.is_valid_url(url):
                    urls.append(url)

            # Remove duplicates while preserving order
            urls = list(dict.fromkeys(urls))
            logger.info(f"Found {len(urls)} article URLs from Investing.com")

        except Exception as e:
            logger.error(f"Failed to get article URLs: {e}")

        return urls

    def parse_article(self, url: str) -> Optional[Dict[str, Any]]:
        """Parse individual article page using Selenium"""
        driver = self._get_driver()

        try:
            logger.info(f"Parsing article: {url}")
            driver.get(url)

            wait = WebDriverWait(driver, 10)
            wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'h1'))
            )

            # Extract title
            title_element = driver.find_element(By.CSS_SELECTOR, 'h1')
            title = title_element.text if title_element else None

            if not title:
                logger.warning(f"No title found for: {url}")
                return None

            # Extract content from article body
            content = ''
            try:
                content_element = driver.find_element(By.CSS_SELECTOR, 'div.article_WYSIWYG__O0uhw')
                if content_element:
                    paragraphs = content_element.find_elements(By.TAG_NAME, 'p')
                    content = '\n\n'.join([p.text for p in paragraphs if p.text.strip()])
            except Exception:
                # Fallback to generic article content
                try:
                    article_element = driver.find_element(By.CSS_SELECTOR, 'article')
                    if article_element:
                        paragraphs = article_element.find_elements(By.TAG_NAME, 'p')
                        content = '\n\n'.join([p.text for p in paragraphs if p.text.strip()])
                except Exception:
                    pass

            # Extract published date
            published_date = None
            try:
                time_element = driver.find_element(By.CSS_SELECTOR, 'time')
                if time_element:
                    published_date = time_element.get_attribute('datetime')
                    # Extract just the date part (YYYY-MM-DD) if it includes time
                    if published_date and 'T' in published_date:
                        published_date = published_date.split('T')[0]
            except Exception:
                pass

            return {
                'title': title,
                'content': content,
                'published_date': published_date
            }

        except Exception as e:
            logger.error(f"Failed to parse article {url}: {e}")
            return None

    def close(self):
        """Clean up Selenium driver and parent resources"""
        if self._driver:
            try:
                self._driver.quit()
                logger.info("Selenium driver closed")
            except Exception as e:
                logger.warning(f"Error closing Selenium driver: {e}")
            self._driver = None
        super().close()
