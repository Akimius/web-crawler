import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from scrapers.base_crawler import BaseCrawler

logger = logging.getLogger(__name__)


class RBCUkraineCrawler(BaseCrawler):
    """RBC Ukraine (РБК-Україна) news crawler with date-based archive support

    Archive URL format: https://www.rbc.ua/ukr/archive/YYYY/MM/DD
    This crawler can fetch articles from specific dates or date ranges.

    Supports crawling:
    - Single date (when start_date and end_date are the same)
    - Date ranges (when start_date and end_date differ)
    - Defaults to today if no dates provided
    """

    def __init__(self, **kwargs):
        """
        Initialize RBC Ukraine crawler

        Args:
            start_date: Start date in YYYY-MM-DD format (passed via kwargs)
            end_date: End date in YYYY-MM-DD format (passed via kwargs)
            **kwargs: Additional arguments passed to BaseCrawler
        """
        # Get start_date and end_date from kwargs if provided
        start_date = kwargs.get('start_date')
        end_date = kwargs.get('end_date')

        # If no dates provided, use today
        if not start_date and not end_date:
            today = datetime.now().strftime('%Y-%m-%d')
            start_date = today
            end_date = today
            logger.info(f"No dates provided, defaulting to today: {today}")
        elif start_date and not end_date:
            # If only start_date provided, use it as both start and end
            end_date = start_date
            logger.info(f"Only start date provided, using single date: {start_date}")
        elif end_date and not start_date:
            # If only end_date provided, use it as both start and end
            start_date = end_date
            logger.info(f"Only end date provided, using single date: {end_date}")

        # Set the initial archive URL (will be overridden if date range)
        date_parts = start_date.split('-')
        archive_url = f"https://www.rbc.ua/ukr/archive/{date_parts[0]}/{date_parts[1]}/{date_parts[2]}"

        super().__init__(
            source_url=archive_url,
            **kwargs
        )

        # Log the date range being crawled
        if start_date == end_date:
            logger.info(f"RBC Ukraine crawler initialized for date: {start_date}")
        else:
            logger.info(f"RBC Ukraine crawler initialized for date range: {start_date} to {end_date}")

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
            # Articles are in <div class="newsline"> > <div> > <a> elements
            article_links = soup.select('div.newsline div a')

            if not article_links:
                # Fallback: try without newsline class
                article_links = soup.select('div.newsline a')

            if not article_links:
                # Try older selectors as fallback
                article_links = soup.select('a.item__title')

            if not article_links:
                # Generic fallback
                article_links = soup.select('div.item a')

            for link in article_links:
                href = link.get('href')
                if href:
                    # RBC uses absolute URLs in archive pages
                    # But ensure we convert relative URLs if any exist
                    absolute_url = self.absolute_url(href)
                    # Only include actual news article URLs (contain /news/ or /ukr/)
                    if self.is_valid_url(absolute_url) and 'rbc.ua' in absolute_url and '/news/' in absolute_url:
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

        # If still no date, try to extract from URL or use today's date as fallback
        if not published_date:
            # Try to extract date from URL pattern: /YYYY/MM/DD/
            import re
            date_match = re.search(r'/(\d{4})/(\d{2})/(\d{2})/', url)
            if date_match:
                published_date = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
            else:
                # Last resort: use today's date
                published_date = datetime.now().strftime('%Y-%m-%d')

        # Normalize date to YYYY-MM-DD format if it contains time
        if published_date:
            # If date contains 'T' or space (ISO format or datetime), extract just the date part
            if 'T' in published_date or ' ' in published_date:
                published_date = published_date.split('T')[0].split(' ')[0]

        return {
            'title': title,
            'content': content,
            'published_date': published_date
        }
