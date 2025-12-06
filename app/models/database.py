import sqlite3
import logging
from datetime import datetime
from typing import Optional, List, Dict, Any
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class Database:
    """SQLite database handler for news crawler"""
    
    def __init__(self, db_path: str):
        self.db_path = db_path
        self.init_database()
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()
    
    def init_database(self):
        """Initialize database schema"""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # Create sources table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS sources (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    url TEXT UNIQUE NOT NULL,
                    parser_class TEXT NOT NULL,
                    is_active INTEGER DEFAULT 1,
                    last_crawled TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            ''')

            # Create articles table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS articles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_id INTEGER NOT NULL,
                    url TEXT UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    content TEXT,
                    published_date TEXT,
                    scraped_date TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    FOREIGN KEY (source_id) REFERENCES sources (id) ON DELETE CASCADE
                )
            ''')

            # Create indexes
            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_articles_source_id
                ON articles(source_id)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_articles_published_date
                ON articles(published_date)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_articles_scraped_date
                ON articles(scraped_date)
            ''')

            cursor.execute('''
                CREATE INDEX IF NOT EXISTS idx_sources_is_active
                ON sources(is_active)
            ''')

            logger.info("Database initialized successfully")


class Source:
    """Model for news sources"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def create(self, name: str, url: str, parser_class: str) -> int:
        """Create a new source"""
        now = datetime.utcnow().isoformat()
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO sources (name, url, parser_class, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?)
            ''', (name, url, parser_class, now, now))
            
            source_id = cursor.lastrowid
            logger.info(f"Created source: {name} (ID: {source_id})")
            return source_id
    
    def get_by_id(self, source_id: int) -> Optional[Dict[str, Any]]:
        """Get source by ID"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM sources WHERE id = ?', (source_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Get source by URL"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM sources WHERE url = ?', (url,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_all_active(self) -> List[Dict[str, Any]]:
        """Get all active sources"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM sources WHERE is_active = 1')
            return [dict(row) for row in cursor.fetchall()]
    
    def update_last_crawled(self, source_id: int):
        """Update last crawled timestamp"""
        now = datetime.utcnow().isoformat()
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE sources 
                SET last_crawled = ?, updated_at = ?
                WHERE id = ?
            ''', (now, now, source_id))
            
            logger.info(f"Updated last_crawled for source ID: {source_id}")
    
    def deactivate(self, source_id: int):
        """Deactivate a source"""
        now = datetime.utcnow().isoformat()
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE sources 
                SET is_active = 0, updated_at = ?
                WHERE id = ?
            ''', (now, source_id))
            
            logger.info(f"Deactivated source ID: {source_id}")


class Article:
    """Model for articles"""
    
    def __init__(self, db: Database):
        self.db = db
    
    def create(self, source_id: int, url: str, title: str,
               content: Optional[str] = None,
               published_date: Optional[str] = None) -> Optional[int]:
        """Create a new article"""
        now = datetime.utcnow().isoformat()

        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            try:
                cursor.execute('''
                    INSERT INTO articles
                    (source_id, url, title, content, published_date, scraped_date, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ''', (source_id, url, title, content, published_date, now, now, now))

                article_id = cursor.lastrowid
                logger.info(f"Created article: {title[:50]}... (ID: {article_id})")
                return article_id

            except sqlite3.IntegrityError:
                logger.warning(f"Article already exists: {url}")
                return None
    
    def get_by_id(self, article_id: int) -> Optional[Dict[str, Any]]:
        """Get article by ID"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM articles WHERE id = ?', (article_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def get_by_url(self, url: str) -> Optional[Dict[str, Any]]:
        """Get article by URL"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM articles WHERE url = ?', (url,))
            row = cursor.fetchone()
            return dict(row) if row else None
    
    def exists(self, url: str) -> bool:
        """Check if article exists"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1 FROM articles WHERE url = ? LIMIT 1', (url,))
            return cursor.fetchone() is not None
    
    def get_by_source(self, source_id: int, limit: int = 100) -> List[Dict[str, Any]]:
        """Get articles by source"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM articles 
                WHERE source_id = ? 
                ORDER BY published_date DESC 
                LIMIT ?
            ''', (source_id, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    def get_by_date_range(self, start_date: str, end_date: str) -> List[Dict[str, Any]]:
        """Get articles by published date range"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT * FROM articles 
                WHERE published_date BETWEEN ? AND ? 
                ORDER BY published_date DESC
            ''', (start_date, end_date))
            return [dict(row) for row in cursor.fetchall()]
    
    def count_by_source(self, source_id: int) -> int:
        """Count articles by source"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) as count FROM articles WHERE source_id = ?', (source_id,))
            return cursor.fetchone()['count']
    
    def get_latest(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get latest articles"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT a.*, s.name as source_name
                FROM articles a
                JOIN sources s ON a.source_id = s.id
                ORDER BY a.published_date DESC
                LIMIT ?
            ''', (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def search(self, keyword: str, limit: int = 20,
               start_date: Optional[str] = None,
               end_date: Optional[str] = None) -> List[Dict[str, Any]]:
        """Search articles by keyword with optional date range"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()

            query = '''
                SELECT a.*, s.name as source_name
                FROM articles a
                JOIN sources s ON a.source_id = s.id
                WHERE (a.title LIKE ? OR a.content LIKE ?)
            '''
            params: List[Any] = [f'%{keyword}%', f'%{keyword}%']

            if start_date and end_date:
                query += ' AND a.published_date BETWEEN ? AND ?'
                params.extend([start_date, end_date])
            elif start_date:
                query += ' AND a.published_date >= ?'
                params.append(start_date)
            elif end_date:
                query += ' AND a.published_date <= ?'
                params.append(end_date)

            query += ' ORDER BY a.published_date DESC LIMIT ?'
            params.append(limit)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def count_total(self) -> int:
        """Count total articles"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT COUNT(*) as count FROM articles')
            return cursor.fetchone()['count']

    def count_scraped_on_date(self, date: str) -> int:
        """Count articles scraped on a specific date"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT COUNT(*) as count FROM articles WHERE DATE(scraped_date) = ?',
                (date,)
            )
            return cursor.fetchone()['count']

    def count_scraped_since(self, date: str) -> int:
        """Count articles scraped since a specific date"""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                'SELECT COUNT(*) as count FROM articles WHERE DATE(scraped_date) >= ?',
                (date,)
            )
            return cursor.fetchone()['count']
