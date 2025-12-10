import logging
from typing import List, Dict, Any, Optional
from models.database import Database, Article, Source
from models.csv_storage import CSVStorage

logger = logging.getLogger(__name__)


class StorageManager:
    """Manages multiple storage backends (SQLite, CSV)"""

    def __init__(self, data_storage: str, db_path: str, csv_dir: str):
        """
        Args:
            data_storage: Comma-separated storage types ("db", "csv", or "db,csv")
            db_path: Path to SQLite database
            csv_dir: Directory for CSV files
        """
        self.backends = self._parse_storage_config(data_storage)

        # Database is always initialized for source management
        self.db = Database(db_path)
        self.source_model = Source(self.db)

        # Article storage backends
        self.article_model: Optional[Article] = None
        self.csv_storage: Optional[CSVStorage] = None

        if 'db' in self.backends:
            self.article_model = Article(self.db)
            logger.info(f"SQLite article storage enabled: {db_path}")

        if 'csv' in self.backends:
            self.csv_storage = CSVStorage(csv_dir)
            logger.info(f"CSV article storage enabled: {self.csv_storage.get_filepath()}")

    def _parse_storage_config(self, data_storage: str) -> List[str]:
        """Parse DATA_STORAGE env var into list of backends"""
        if not data_storage:
            return ['db']  # Default to SQLite only

        # Strip quotes that may come from .env file
        data_storage = data_storage.strip('"\'')

        backends = [b.strip().lower() for b in data_storage.split(',')]
        valid = {'db', 'csv'}
        backends = [b for b in backends if b in valid]

        if not backends:
            logger.warning("No valid storage backends, defaulting to 'db'")
            return ['db']

        logger.info(f"Storage backends configured: {backends}")
        return backends

    def create_article_batch(self, source_id: int, source_name: str,
                             articles: List[Dict[str, Any]],
                             batch_size: int = 10) -> Dict[str, int]:
        """Save articles to all configured backends

        Returns combined stats (uses DB stats if available, else CSV)
        """
        db_result = {'saved': 0, 'skipped': 0}
        csv_result = {'saved': 0, 'skipped': 0}

        # Save to SQLite
        if self.article_model:
            db_result = self.article_model.create_batch(
                source_id=source_id,
                articles=articles,
                batch_size=batch_size
            )

        # Save to CSV
        if self.csv_storage:
            csv_result = self.csv_storage.create_batch(
                source_id=source_id,
                source_name=source_name,
                articles=articles
            )

        # Return DB stats if available (has dedup info), else CSV stats
        if self.article_model:
            return db_result
        return csv_result

    def has_database(self) -> bool:
        """Check if database backend is enabled"""
        return self.db is not None

    def has_csv(self) -> bool:
        """Check if CSV backend is enabled"""
        return self.csv_storage is not None

    def get_csv_filepath(self) -> Optional[str]:
        """Get the current CSV file path"""
        if self.csv_storage:
            return self.csv_storage.get_filepath()
        return None