import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from scrapers.base_crawler import BaseCrawler

logger = logging.getLogger(__name__)


class BBCNewsCrawler(BaseCrawler):
    """BBC News crawler implementation"""
    
    def __init__(self, **kwargs):
        super().__init__(
            source_url='https://www.bbc.com/news',
            **kwargs
        )
    
    def get_article_urls(self) -> List[str]:
        """Get article URLs from BBC News homepage"""
        html = self.fetch_page(self.source_url)
        if not html:
            return []
        
        soup = self.parse_html(html)
        
        # BBC uses specific data attributes for article links
        article_links = soup.select('a[data-testid="internal-link"]')
        
        urls = []
        for link in article_links:
            href = link.get('href')
            if href and '/news/articles/' in href:
                absolute_url = self.absolute_url(href)
                if self.is_valid_url(absolute_url):
                    urls.append(absolute_url)
        
        # Remove duplicates while preserving order
        unique_urls = list(dict.fromkeys(urls))
        logger.info(f"Found {len(unique_urls)} unique article URLs from BBC News")
        
        return unique_urls[:20]  # Limit to 20 most recent articles
    
    def parse_article(self, url: str) -> Optional[Dict[str, Any]]:
        """Parse BBC News article"""
        html = self.fetch_page(url)
        if not html:
            return None
        
        soup = self.parse_html(html)
        
        # Extract title
        title = self.extract_text(soup, 'h1#main-heading')
        if not title:
            # Fallback to other possible title selectors
            title = self.extract_text(soup, 'h1')
        
        if not title:
            logger.warning(f"No title found for: {url}")
            return None
        
        # Extract article content
        content_blocks = soup.select('div[data-component="text-block"] p')
        content = '\n\n'.join([p.get_text(strip=True) for p in content_blocks if p.get_text(strip=True)])
        
        if not content:
            # Fallback to generic article content
            article_body = soup.select_one('article')
            if article_body:
                paragraphs = article_body.find_all('p')
                content = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
        
        # Extract author (BBC often doesn't show author prominently)
        author = self.extract_text(soup, 'div[data-component="byline-block"]')
        
        # Extract published date
        published_date = None
        time_element = soup.select_one('time')
        if time_element:
            published_date = time_element.get('datetime')
            if not published_date:
                published_date = time_element.get_text(strip=True)
        
        # Generate summary
        summary = content[:200] + '...' if len(content) > 200 else content
        
        return {
            'title': title,
            'content': content,
            'author': author if author else 'BBC News',
            'published_date': published_date,
            'summary': summary
        }
