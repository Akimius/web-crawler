import csv
import os
import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class CSVStorage:
    """CSV file storage for articles with timestamped filenames"""

    FIELDNAMES = ['source_id', 'source_name', 'url', 'title',
                  'content', 'published_date', 'scraped_date']

    def __init__(self, csv_dir: str):
        """
        Args:
            csv_dir: Directory to store CSV files
        """
        self.csv_dir = csv_dir
        self.csv_path = self._generate_filepath()
        self._file_initialized = False
        self._ensure_directory()

    def _ensure_directory(self):
        """Create directory if it doesn't exist"""
        if self.csv_dir and not os.path.exists(self.csv_dir):
            os.makedirs(self.csv_dir)
            logger.info(f"Created CSV directory: {self.csv_dir}")

    def _generate_filepath(self) -> str:
        """Generate timestamped CSV filename"""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"articles_{timestamp}.csv"
        return os.path.join(self.csv_dir, filename)

    def _ensure_header(self):
        """Write header if file doesn't exist yet"""
        if self._file_initialized:
            return

        if not os.path.exists(self.csv_path):
            with open(self.csv_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES)
                writer.writeheader()
            logger.info(f"Created new CSV file: {self.csv_path}")

        self._file_initialized = True

    def create_batch(self, source_id: int, source_name: str,
                     articles: List[Dict[str, Any]]) -> Dict[str, int]:
        """Save articles to CSV file

        Args:
            source_id: The source ID
            source_name: Human-readable source name
            articles: List of article dicts

        Returns:
            Dict with 'saved' and 'skipped' counts
        """
        saved = 0
        skipped = 0
        now = datetime.utcnow().isoformat()

        self._ensure_header()

        try:
            with open(self.csv_path, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=self.FIELDNAMES,
                                        extrasaction='ignore')

                for article in articles:
                    url = article.get('url')
                    title = article.get('title')

                    if not url or not title:
                        skipped += 1
                        continue

                    row = {
                        'source_id': source_id,
                        'source_name': source_name,
                        'url': url,
                        'title': title,
                        'content': self._sanitize_content(article.get('content', '')),
                        'published_date': article.get('published_date', ''),
                        'scraped_date': now
                    }

                    writer.writerow(row)
                    saved += 1

        except Exception as e:
            logger.error(f"Error writing to CSV: {e}")
            raise

        logger.info(f"CSV batch: {saved} saved, {skipped} skipped")
        return {'saved': saved, 'skipped': skipped}

    @staticmethod
    def _sanitize_content(content: str) -> str:
        """Sanitize content for CSV storage"""
        if not content:
            return ''
        # Replace newlines with space for cleaner CSV
        return ' '.join(content.split())

    def get_filepath(self) -> str:
        """Return the current CSV file path"""
        return self.csv_path