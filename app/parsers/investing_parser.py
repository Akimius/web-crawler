import logging
import time
from typing import List, Dict, Any, Optional
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from scrapers.base_crawler import BaseCrawler

logger = logging.getLogger(__name__)


class InvestingCrawler(BaseCrawler):
    """Investing.com Gold News crawler using Selenium for JS-rendered content.

    Extracts article data directly from the news list page without following links.
    Supports optional email/password authentication for accessing premium content.
    """

    def __init__(self, email: str = None, password: str = None,
                 page_start: int = None, page_end: int = None, **kwargs):
        self._page_start = page_start or 1
        self._page_end = page_end or self._page_start
        super().__init__(
            source_url='https://www.investing.com/commodities/gold-news',
            **kwargs
        )
        self._driver = None
        self._articles_cache = []  # Store articles extracted from list page
        self._email = 'akim.savchenko@gmail.com'
        self._password = 'ab123456789'
        self._logged_in = False
        logger.info(f"InvestingCrawler initialized for pages {self._page_start} to {self._page_end}")

    def _get_driver(self):
        """Lazy initialization of Selenium driver"""
        if self._driver is None:
            from browser import get_chrome_driver
            self._driver = get_chrome_driver()
            logger.info("Selenium driver initialized for Investing.com")
        return self._driver

    def _generate_page_urls(self) -> List[str]:
        """Generate URLs for each page in the configured range"""
        return [
            f"{self.source_url}/{page}"
            for page in range(self._page_start, self._page_end + 1)
        ]

    def _login(self) -> bool:
        """Authenticate with Investing.com using email/password."""
        if self._logged_in or not self._email or not self._password:
            return self._logged_in

        driver = self._get_driver()
        try:
            logger.info("Attempting to log in to Investing.com")
            driver.get("https://www.investing.com")

            wait = WebDriverWait(driver, 5)

            # Try to dismiss cookie consent popup if present
            # try:
            #     cookie_btn = WebDriverWait(driver, 5).until(
            #         EC.element_to_be_clickable(
            #             (By.CSS_SELECTOR, '#onetrust-accept-btn-handler, [id*="accept"], button[class*="accept"]'))
            #     )
            #     cookie_btn.click()
            #     logger.debug("Dismissed cookie consent popup")
            #     time.sleep(1)
            # except TimeoutException:
            #     pass

            # Click sign-in button to open login modal
            sign_in_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Sign In')]/.."))
            )
            sign_in_btn.click()
            time.sleep(2)

            # Click "Sign in with Email" button (site shows social login options first)
            email_login_btn = wait.until(
                EC.element_to_be_clickable(
                    (By.CSS_SELECTOR, 'button[class*="email"], a[class*="email"]'))
            )
            email_login_btn.click()
            time.sleep(1)

            # Wait for login form and fill credentials
            email_field = wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, 'input[type="email"], input[name="email"], input[placeholder*="mail"]'))
            )
            email_field.clear()
            email_field.send_keys(self._email)

            password_field = driver.find_element(
                By.CSS_SELECTOR, 'input[type="password"], input[name="password"]')
            password_field.clear()
            password_field.send_keys(self._password)

            # Submit login form using JS click for reliability
            submit_btn = driver.find_element(
                By.CSS_SELECTOR, 'button[type="submit"], input[type="submit"]')
            driver.execute_script("arguments[0].scrollIntoView(true);", submit_btn)
            time.sleep(0.5)
            driver.execute_script("arguments[0].click();", submit_btn)

            # Wait for login to complete
            time.sleep(3)
            wait.until(
                EC.presence_of_element_located(
                    (By.CSS_SELECTOR, '[data-test="user-menu"], .user-menu, [class*="userMenu"], [class*="avatar"], [class*="profile"]'))
            )

            self._logged_in = True
            logger.info("Successfully logged in to Investing.com")
            return True

        except TimeoutException as e:
            logger.error(f"Login timeout - element not found: {e}")
            return False
        except Exception as e:
            logger.error(f"Failed to log in to Investing.com: {e}")
            return False

    def get_article_urls(self) -> List[str]:
        """Get article URLs and extract article data from news list pages."""
        driver = self._get_driver()
        self._articles_cache = []
        urls = []

        # Attempt login if credentials provided
        if self._email and self._password:
            self._login()

        # Get all page URLs to crawl
        page_urls = self._generate_page_urls()
        total_pages = len(page_urls)
        logger.info(f"Crawling {total_pages} page(s) from Investing.com")

        for page_num, page_url in enumerate(page_urls, start=1):
            try:
                logger.info(f"Fetching page {page_num}/{total_pages}: {page_url}")
                driver.get(page_url)

                wait = WebDriverWait(driver, 10)
                wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, 'ul[data-test="news-list"]'))
                )

                # Find all article items in the news list
                news_list = driver.find_element(By.CSS_SELECTOR, 'ul[data-test="news-list"]')
                article_items = news_list.find_elements(By.CSS_SELECTOR, 'li')

                page_articles = 0
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

                        # Skip PRO links (premium content)
                        if '/pro/' in url.lower():
                            logger.debug(f"Skipping PRO article: {title[:50]}...")
                            continue

                        # Store the article data
                        self._articles_cache.append({
                            'url': url,
                            'title': title,
                            'description': description,
                            'published_date': published_date
                        })
                        urls.append(url)
                        page_articles += 1
                        logger.debug(f"Extracted: {title[:50]}... ({published_date})")

                    except Exception as e:
                        logger.debug(f"Failed to extract article from list item: {e}")
                        continue

                logger.info(f"Page {page_num}: found {page_articles} articles")

            except Exception as e:
                logger.error(f"Failed to get articles from page {page_url}: {e}")
                continue

        logger.info(f"Total: found {len(urls)} articles from {total_pages} page(s)")

        return urls

    def parse_article(self, url: str) -> Optional[Dict[str, Any]]:
        """Fetch article page and extract full content text."""
        # Get cached metadata
        cached = None
        for article in self._articles_cache:
            if article['url'] == url:
                cached = article
                break

        if not cached:
            logger.warning(f"Article not found in cache: {url}")
            return None

        driver = self._get_driver()

        try:
            # Rate limiting between article fetches
            time.sleep(self.request_delay)

            logger.info(f"Fetching article: {cached['title'][:50]}...")
            driver.get(url)

            # Wait for page to load (check for body first)
            wait = WebDriverWait(driver, 10)
            wait.until(EC.presence_of_element_located((By.TAG_NAME, 'body')))

            # Handle Cloudflare challenge - wait up to 15 seconds for it to clear
            for _ in range(15):
                if "just a moment" not in driver.title.lower():
                    break
                logger.debug("Waiting for Cloudflare challenge...")
                time.sleep(1)

            # Give page time to render JS content
            time.sleep(2)

            # Try multiple selectors for article content
            content = ''
            selectors = [
                'div#article .article_WYSIWYG__O0uhw',
                'div#article .articlePage',
                'div#article',
                'article .article-content',
                '.article-content',
                '[data-test="article-content"]',
            ]

            for selector in selectors:
                try:
                    article_div = driver.find_element(By.CSS_SELECTOR, selector)
                    content = article_div.text.strip()
                    if content and len(content) > 100:  # Meaningful content
                        logger.info(f"Extracted {len(content)} chars using selector: {selector}")
                        break
                except NoSuchElementException:
                    continue

            if not content or len(content) < 100:
                # Debug: save screenshot to see what's on the page
                try:
                    driver.save_screenshot('/app/data/debug_article.png')
                    logger.warning(f"Saved debug screenshot, page title: {driver.title}")
                except Exception:
                    pass
                logger.warning(f"Could not extract content, using description for: {url}")
                content = cached.get('description', '')

            return {
                'title': cached['title'],
                'content': content,
                'published_date': cached['published_date']
            }

        except TimeoutException:
            logger.error(f"Timeout loading article: {url}")
            return {
                'title': cached['title'],
                'content': cached.get('description', ''),
                'published_date': cached['published_date']
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
