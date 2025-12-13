import logging
import os
from typing import List, Dict, Any, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from scrapers.base_crawler import BaseCrawler

logger = logging.getLogger(__name__)


class InvestingCrawler(BaseCrawler):
    """Investing.com Gold News crawler using Selenium for JS-rendered content.

    Extracts article data directly from the news list page without following links.
    Supports optional email/password authentication for accessing premium content.
    """

    def __init__(self, email: str = None, password: str = None, **kwargs):
        super().__init__(
            source_url='https://www.investing.com/commodities/gold-news/12',
            **kwargs
        )
        self._driver = None
        self._articles_cache = []  # Store articles extracted from list page
        self._email = email or os.getenv('INVESTING_EMAIL')
        self._password = password or os.getenv('INVESTING_PASSWORD')
        self._logged_in = False

    def _get_driver(self):
        """Lazy initialization of Selenium driver"""
        if self._driver is None:
            from browser import get_chrome_driver
            self._driver = get_chrome_driver()
            logger.info("Selenium driver initialized for Investing.com")
        return self._driver

    def _login(self) -> bool:
        """Authenticate with Investing.com using email/password."""
        if self._logged_in or not self._email or not self._password:
            return self._logged_in

        driver = self._get_driver()
        try:
            logger.info("Attempting to log in to Investing.com")
            driver.get("https://www.investing.com")

            wait = WebDriverWait(driver, 10)

            # Click sign-in button to open login modal
            sign_in_btn = wait.until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, 'a[data-test="sign-in-button"], .login-btn, [class*="signIn"]'))
            )
            sign_in_btn.click()

            # Wait for login form and fill credentials
            email_field = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'input[type="email"], input[name="email"], #loginFormUser_email'))
            )
            email_field.clear()
            email_field.send_keys(self._email)

            password_field = driver.find_element(By.CSS_SELECTOR, 'input[type="password"], input[name="password"], #loginForm_password')
            password_field.clear()
            password_field.send_keys(self._password)

            # Submit login form
            submit_btn = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"], input[type="submit"], .login-btn-submit')
            submit_btn.click()

            # Wait for login to complete (check for user menu or profile element)
            wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, '[data-test="user-menu"], .user-menu, [class*="userMenu"]'))
            )

            self._logged_in = True
            logger.info("Successfully logged in to Investing.com")
            return True

        except Exception as e:
            logger.error(f"Failed to log in to Investing.com: {e}")
            return False

    def get_article_urls(self) -> List[str]:
        """Get article URLs and extract article data from news list page."""
        driver = self._get_driver()
        self._articles_cache = []
        urls = []

        # Attempt login if credentials provided
        if self._email and self._password:
            self._login()

        try:
            logger.info(f"Fetching: {self.source_url}")
            driver.get(self.source_url)

            wait = WebDriverWait(driver, 10)
            wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, 'ul[data-test="news-list"]'))
            )

            # Find all article items in the news list
            news_list = driver.find_element(By.CSS_SELECTOR, 'ul[data-test="news-list"]')
            article_items = news_list.find_elements(By.CSS_SELECTOR, 'li')

            for item in article_items:
                try:
                    # Get title and URL from link
                    link = item.find_element(By.CSS_SELECTOR, 'a[data-test="article-title-link"]')
                    url = link.get_attribute("href")
                    title = link.text.strip()

                    if not url or not title:
                        continue

                    # Get description
                    description = ''
                    try:
                        desc_elem = item.find_element(By.CSS_SELECTOR, 'p[data-test="article-description"]')
                        description = desc_elem.text.strip()
                    except Exception:
                        pass

                    # Get published date
                    published_date = None
                    try:
                        time_elem = item.find_element(By.CSS_SELECTOR, 'time[data-test="article-publish-date"]')
                        datetime_attr = time_elem.get_attribute('datetime')
                        if datetime_attr:
                            # Extract date from "2025-12-11 17:24:48" format
                            published_date = datetime_attr.split(' ')[0]
                    except Exception:
                        pass

                    # Store the article data
                    self._articles_cache.append({
                        'url': url,
                        'title': title,
                        'content': description,
                        'published_date': published_date
                    })
                    urls.append(url)
                    logger.debug(f"Extracted: {title[:50]}... ({published_date})")

                except Exception as e:
                    logger.debug(f"Failed to extract article from list item: {e}")
                    continue

            logger.info(f"Found {len(urls)} articles from Investing.com")

        except Exception as e:
            logger.error(f"Failed to get articles: {e}")

        return urls

    def parse_article(self, url: str) -> Optional[Dict[str, Any]]:
        """Return cached article data (already extracted from list page)."""
        for article in self._articles_cache:
            if article['url'] == url:
                logger.info(f"Returning cached article: {article['title'][:50]}...")
                return {
                    'title': article['title'],
                    'content': article['content'],
                    'published_date': article['published_date']
                }

        logger.warning(f"Article not found in cache: {url}")
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
