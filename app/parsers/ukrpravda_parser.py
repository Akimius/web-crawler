import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from app.scrapers.base_crawler import BaseCrawler

logger = logging.getLogger(__name__)


class UkrPravdaCrawler(BaseCrawler):
    """Ukrayinska Pravda crawler implementation"""
    
    def __init__(self, **kwargs):
        super().__init__(
            source_url='https://www.pravda.com.ua/news/',
            **kwargs
        )
    
    def get_article_urls(self) -> List[str]:
        """Get article URLs from Ukrayinska Pravda"""
        html = self.fetch_page(self.source_url)
        if not html:
            return []
        
        soup = self.parse_html(html)
        
        # Find article links in news blocks
        article_links = soup.select('div.article_header a.article_header')
        
        urls = []
        for link in article_links:
            href = link.get('href')
            if href:
                absolute_url = self.absolute_url(href)
                if self.is_valid_url(absolute_url) and '/news/' in absolute_url:
                    urls.append(absolute_url)
        
        # Remove duplicates while preserving order
        unique_urls = list(dict.fromkeys(urls))
        logger.info(f"Found {len(unique_urls)} unique article URLs from Ukrayinska Pravda")
        
        return unique_urls[:20]  # Limit to 20 most recent articles
    
    def parse_article(self, url: str) -> Optional[Dict[str, Any]]:
        """Parse Ukrayinska Pravda article"""
        html = self.fetch_page(url)
        if not html:
            return None
        
        soup = self.parse_html(html)
        
        # Extract title
        title = self.extract_text(soup, 'h1.post_title')
        if not title:
            title = self.extract_text(soup, 'h1')
        
        if not title:
            logger.warning(f"No title found for: {url}")
            return None
        
        # Extract article content
        article_body = soup.select_one('div.post_text')
        if article_body:
            paragraphs = article_body.find_all('p', class_=lambda x: x != 'article_news_bot')
            content = '\n\n'.join([p.get_text(strip=True) for p in paragraphs if p.get_text(strip=True)])
        else:
            content = ''
        
        # Extract author
        author = self.extract_text(soup, 'div.post_author a')
        
        # Extract published date
        published_date = None
        date_element = soup.select_one('div.post_time')
        if date_element:
            published_date = date_element.get_text(strip=True)
        
        # Generate summary
        summary = content[:200] + '...' if len(content) > 200 else content
        
        return {
            'title': title,
            'content': content,
            'author': author if author else 'Ukrayinska Pravda',
            'published_date': published_date,
            'summary': summary
        }
