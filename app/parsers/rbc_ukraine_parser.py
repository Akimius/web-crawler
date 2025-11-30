import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from scrapers.base_crawler import BaseCrawler

logger = logging.getLogger(__name__)


class RBCUkraineCrawler(BaseCrawler):
    """RBC Ukraine (РБК-Україна) news crawler with date-based archive support

    Archive URL format: https://www.rbc.ua/ukr/archive/YYYY/MM/DD
    This crawler can fetch articles from specific dates or date ranges.
    """

    def __init__(self, archive_date: str = None, **kwargs):
        """
        Initialize RBC Ukraine crawler

        Args:
            archive_date: Optional date in YYYY-MM-DD format.
                         If not provided, uses today's date.
            **kwargs: Additional arguments passed to BaseCrawler
        """
        # Use provided date or today's date
        if archive_date:
            self.archive_date = archive_date
        else:
            self.archive_date = datetime.now().strftime('%Y-%m-%d')

        # Convert YYYY-MM-DD to YYYY/MM/DD for URL
        date_parts = self.archive_date.split('-')
        archive_url = f"https://www.rbc.ua/ukr/archive/{date_parts[0]}/{date_parts[1]}/{date_parts[2]}"

        super().__init__(
            source_url=archive_url,
            **kwargs
        )

        logger.info(f"RBC Ukraine crawler initialized for date: {self.archive_date}")

    def _generate_archive_urls(self) -> List[str]:
        """Generate archive URLs based on date range if configured"""
        urls = [self.source_url]

        # If date filtering is enabled, generate URLs for the date range
        if self.start_date and self.end_date:
            try:
                start = datetime.strptime(self.start_date, '%Y-%m-%d')
                end = datetime.strptime(self.end_date, '%Y-%m-%d')

                # Generate URL for each date in range
                urls = []
                current = start
                while current <= end:
                    date_str = current.strftime('%Y/%m/%d')
                    url = f"https://www.rbc.ua/ukr/archive/{date_str}"
                    urls.append(url)
                    current += timedelta(days=1)

                logger.info(f"Generated {len(urls)} archive URLs for date range")
            except Exception as e:
                logger.warning(f"Could not generate date range URLs: {e}")
                urls = [self.source_url]

        return urls

    def get_article_urls(self) -> List[str]:
        """Get article URLs from RBC Ukraine archive page(s)"""
        archive_urls = self._generate_archive_urls()
        all_article_urls = []

        for archive_url in archive_urls:
            logger.info(f"Fetching articles from: {archive_url}")
            html = self.fetch_page(archive_url)
            if not html:
                continue

            soup = self.parse_html(html)

            # RBC Ukraine archive page structure
            # Articles are typically in elements with specific classes
            article_links = soup.select('a.item__title')

            # Fallback selectors if the main one doesn't work
            if not article_links:
                article_links = soup.select('div.item a')

            if not article_links:
                # Try generic article links
                article_links = soup.select('article a, .article a, .news-item a')

            for link in article_links:
                href = link.get('href')
                if href:
                    # RBC uses relative URLs, convert to absolute
                    absolute_url = self.absolute_url(href)
                    if self.is_valid_url(absolute_url) and 'rbc.ua' in absolute_url:
                        all_article_urls.append(absolute_url)

        # Remove duplicates while preserving order
        unique_urls = list(dict.fromkeys(all_article_urls))
        logger.info(f"Found {len(unique_urls)} unique article URLs from RBC Ukraine")

        return unique_urls

    def parse_article(self, url: str) -> Optional[Dict[str, Any]]:
        """Parse RBC Ukraine article"""
        html = self.fetch_page(url)
        if not html:
            return None

        soup = self.parse_html(html)

        # Extract title
        title = self.extract_text(soup, 'h1.article__title')
        if not title:
            title = self.extract_text(soup, 'h1')

        if not title:
            logger.warning(f"No title found for: {url}")
            return None

        # Extract article content
        # RBC typically uses article__text or similar classes
        content_container = soup.select_one('div.article__text')
        if content_container:
            paragraphs = content_container.find_all('p')
            content = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
        else:
            # Fallback to generic article content
            article_body = soup.select_one('article')
            if article_body:
                paragraphs = article_body.find_all('p')
                content = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
            else:
                content = ''

        # Extract author
        author = self.extract_text(soup, 'div.article__author')
        if not author:
            author = self.extract_text(soup, 'span.author, div.author, a.author')

        # Extract published date
        published_date = None

        # Try to get from time element
        time_element = soup.select_one('time')
        if time_element:
            published_date = time_element.get('datetime')
            if not published_date:
                published_date = time_element.get_text(strip=True)

        # Try to get from article meta
        if not published_date:
            date_element = soup.select_one('div.article__date, span.article__date')
            if date_element:
                published_date = date_element.get_text(strip=True)

        # Try to get from meta tags
        if not published_date:
            meta_date = soup.select_one('meta[property="article:published_time"]')
            if meta_date:
                published_date = meta_date.get('content')

        # If still no date, use the archive date from the URL
        if not published_date and self.archive_date:
            published_date = self.archive_date

        # Generate summary
        summary = content[:200] + '...' if len(content) > 200 else content

        return {
            'title': title,
            'content': content,
            'author': author if author else 'РБК-Україна',
            'published_date': published_date,
            'summary': summary
        }
