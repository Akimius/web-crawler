import logging
import os
from typing import List, Dict, Any, Type
from models.database import Source
from models.storage import StorageManager
from scrapers.base_crawler import BaseCrawler
# Commented out other parsers - only using RBC Ukraine for now
# from parsers.bbc_parser import BBCNewsCrawler
# from parsers.guardian_parser import GuardianNewsCrawler
# from parsers.ukrpravda_parser import UkrPravdaCrawler
from parsers.rbc_ukraine_parser import RBCUkraineCrawler

logger = logging.getLogger(__name__)


class CrawlerManager:
    """Manages all crawlers and coordinates scraping"""

    # Registry of available parsers
    # Only RBC Ukraine parser is active - others commented out
    PARSERS: Dict[str, Type[BaseCrawler]] = {
        'RBCUkraineCrawler': RBCUkraineCrawler,
        # 'BBCNewsCrawler': BBCNewsCrawler,
        # 'GuardianNewsCrawler': GuardianNewsCrawler,
        # 'UkrPravdaCrawler': UkrPravdaCrawler,
    }
    
    def __init__(self, db_path: str, user_agent: str = None,
                 request_delay: float = 1.0, timeout: int = 30,
                 start_date: str = None, end_date: str = None,
                 data_storage: str = 'db', csv_dir: str = 'data'):
        # Initialize storage manager for DB and/or CSV
        self.storage = StorageManager(data_storage, db_path, csv_dir)

        # Source model from storage manager (DB always available for sources)
        self.source_model = self.storage.source_model

        self.user_agent = user_agent
        self.request_delay = request_delay
        self.timeout = timeout
        self.start_date = start_date
        self.end_date = end_date

        self.stats = {
            'sources_crawled': 0,
            'articles_found': 0,
            'articles_saved': 0,
            'articles_skipped': 0,
            'errors': 0
        }
    
    def add_source(self, name: str, url: str, parser_class: str) -> int:
        """Add a new news source"""
        if parser_class not in self.PARSERS:
            raise ValueError(f"Parser '{parser_class}' not found. Available: {list(self.PARSERS.keys())}")
        
        existing = self.source_model.get_by_url(url)
        if existing:
            logger.info(f"Source already exists: {name}")
            return existing['id']
        
        return self.source_model.create(name, url, parser_class)
    
    def crawl_source(self, source_id: int) -> Dict[str, int]:
        """Crawl a single source"""
        source = self.source_model.get_by_id(source_id)
        if not source:
            raise ValueError(f"Source with ID {source_id} not found")
        
        if not source['is_active']:
            logger.warning(f"Source is inactive: {source['name']}")
            return {'found': 0, 'saved': 0, 'skipped': 0}
        
        parser_class = source['parser_class']
        if parser_class not in self.PARSERS:
            raise ValueError(f"Parser '{parser_class}' not found")
        
        logger.info(f"Crawling source: {source['name']} ({source['url']})")
        
        # Initialize crawler
        crawler_cls = self.PARSERS[parser_class]
        crawler = crawler_cls(
            user_agent=self.user_agent,
            request_delay=self.request_delay,
            timeout=self.timeout,
            start_date=self.start_date,
            end_date=self.end_date
        )
        
        try:
            # Track stats
            stats = {'found': 0, 'saved': 0, 'skipped': 0}

            def save_batch(articles_batch):
                """Callback to save articles to all configured backends"""
                stats['found'] += len(articles_batch)
                result = self.storage.create_article_batch(
                    source_id=source_id,
                    source_name=source['name'],
                    articles=articles_batch,
                    batch_size=len(articles_batch)
                )
                stats['saved'] += result['saved']
                stats['skipped'] += result['skipped']

            # Crawl articles with callback to save every 10 articles
            crawler.crawl(on_batch=save_batch, batch_size=10)

            # Update source last_crawled timestamp
            self.source_model.update_last_crawled(source_id)

            logger.info(f"Crawl complete: {stats['saved']} saved, {stats['skipped']} skipped")

            return stats
            
        except Exception as e:
            logger.error(f"Error crawling source {source['name']}: {e}", exc_info=True)
            raise
        
        finally:
            crawler.close()
    
    def crawl_all_sources(self) -> Dict[str, Any]:
        """Crawl all active sources"""
        sources = self.source_model.get_all_active()
        
        if not sources:
            logger.warning("No active sources found")
            return self.stats
        
        logger.info(f"Starting crawl for {len(sources)} sources")
        
        self.stats = {
            'sources_crawled': 0,
            'articles_found': 0,
            'articles_saved': 0,
            'articles_skipped': 0,
            'errors': 0
        }
        
        for source in sources:
            try:
                result = self.crawl_source(source['id'])
                
                self.stats['sources_crawled'] += 1
                self.stats['articles_found'] += result['found']
                self.stats['articles_saved'] += result['saved']
                self.stats['articles_skipped'] += result['skipped']
                
            except Exception as e:
                logger.error(f"Failed to crawl source {source['name']}: {e}")
                self.stats['errors'] += 1
        
        logger.info(f"Crawl complete: {self.stats}")
        return self.stats
    
    def get_stats(self) -> Dict[str, Any]:
        """Get crawling statistics"""
        return self.stats
    
    def list_sources(self) -> List[Dict[str, Any]]:
        """List all sources"""
        return self.source_model.get_all_active()
    
    def deactivate_source(self, source_id: int):
        """Deactivate a source"""
        self.source_model.deactivate(source_id)
    
    @classmethod
    def get_available_parsers(cls) -> List[str]:
        """Get list of available parser classes"""
        return list(cls.PARSERS.keys())
