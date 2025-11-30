import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from scrapers.base_crawler import BaseCrawler

logger = logging.getLogger(__name__)


class GuardianNewsCrawler(BaseCrawler):
    """The Guardian News crawler implementation"""
    
    def __init__(self, **kwargs):
        super().__init__(
            source_url='https://www.theguardian.com/international',
            **kwargs
        )
    
    def get_article_urls(self) -> List[str]:
        """Get article URLs from The Guardian homepage"""
        html = self.fetch_page(self.source_url)
        if not html:
            return []
        
        soup = self.parse_html(html)
        
        # Guardian uses specific class for article links
        article_links = soup.select('a[data-link-name="article"]')
        
        urls = []
        for link in article_links:
            href = link.get('href')
            if href and href.startswith('https://www.theguardian.com/'):
                if self.is_valid_url(href):
                    urls.append(href)
        
        # Remove duplicates while preserving order
        unique_urls = list(dict.fromkeys(urls))
        logger.info(f"Found {len(unique_urls)} unique article URLs from The Guardian")
        
        return unique_urls[:20]  # Limit to 20 most recent articles
    
    def parse_article(self, url: str) -> Optional[Dict[str, Any]]:
        """Parse Guardian article"""
        html = self.fetch_page(url)
        if not html:
            return None
        
        soup = self.parse_html(html)
        
        # Extract title
        title = self.extract_text(soup, 'h1[itemprop="headline"]')
        if not title:
            title = self.extract_text(soup, 'h1')
        
        if not title:
            logger.warning(f"No title found for: {url}")
            return None
        
        # Extract article content
        content_blocks = soup.select('div[data-gu-name="body"] p')
        content = '\n\n'.join([p.get_text(strip=True) for p in content_blocks if p.get_text(strip=True)])
        
        if not content:
            # Fallback to article body
            article_body = soup.select_one('article div.article-body-viewer-selector')
            if article_body:
                paragraphs = article_body.find_all('p')
                content = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
        
        # Extract author
        author = self.extract_text(soup, 'a[rel="author"]')
        if not author:
            author = self.extract_text(soup, 'address a')
        
        # Extract published date
        published_date = None
        time_element = soup.select_one('time')
        if time_element:
            published_date = time_element.get('datetime')
        
        # Generate summary
        summary = content[:200] + '...' if len(content) > 200 else content
        
        return {
            'title': title,
            'content': content,
            'author': author if author else 'The Guardian',
            'published_date': published_date,
            'summary': summary
        }
