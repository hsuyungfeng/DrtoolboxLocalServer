"""Query Cache Manager with TTL for HIS queries."""

import sqlite3
import hashlib
import json
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class QueryCache:
    """Cache manager for HIS queries with 1-hour TTL."""

    def __init__(self, db_path: str = "data/clinic.db"):
        self.db_path = db_path
        self._init_table()

    def _init_table(self):
        """Create cache table if not exists."""
        conn = sqlite3.connect(self.db_path)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS query_cache (
                id INTEGER PRIMARY KEY,
                query_hash TEXT UNIQUE NOT NULL,
                query_text TEXT NOT NULL,
                result_json TEXT NOT NULL,
                ttl_seconds INTEGER DEFAULT 3600,
                cached_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                hit_count INTEGER DEFAULT 0
            )
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_query_hash
            ON query_cache(query_hash)
        """)
        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_expires_at
            ON query_cache(expires_at)
        """)
        conn.commit()
        conn.close()

    def _get_query_hash(self, query: str, params: tuple) -> str:
        """Generate hash of query + params."""
        key = f"{query}:{json.dumps(params)}"
        return hashlib.sha256(key.encode()).hexdigest()

    def get(self, query: str, params: tuple = ()) -> Optional[List[Dict[str, Any]]]:
        """Get cached result if valid, else None."""
        query_hash = self._get_query_hash(query, params)
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute(
            "SELECT result_json FROM query_cache WHERE query_hash = ? AND expires_at > datetime('now')",
            (query_hash,)
        )
        row = cursor.fetchone()
        conn.close()

        if row:
            logger.debug(f"Cache hit for {query[:50]}...")
            return json.loads(row["result_json"])
        return None

    def set(self, query: str, params: tuple, result: List[Dict[str, Any]], ttl_seconds: int = 3600):
        """Store result in cache with TTL."""
        query_hash = self._get_query_hash(query, params)
        result_json = json.dumps(result)
        expires_at = (datetime.now() + timedelta(seconds=ttl_seconds)).isoformat()

        conn = sqlite3.connect(self.db_path)
        try:
            conn.execute(
                """INSERT OR REPLACE INTO query_cache 
                   (query_hash, query_text, result_json, ttl_seconds, expires_at) 
                   VALUES (?, ?, ?, ?, ?)""",
                (query_hash, query, result_json, ttl_seconds, expires_at)
            )
            conn.commit()
            logger.debug(f"Cached result for {query[:50]}... (TTL: {ttl_seconds}s)")
        finally:
            conn.close()

    def invalidate(self, query: Optional[str] = None, params: Optional[tuple] = None):
        """Invalidate cache entry or all entries."""
        conn = sqlite3.connect(self.db_path)
        if query:
            query_hash = self._get_query_hash(query, params or ())
            conn.execute("DELETE FROM query_cache WHERE query_hash = ?", (query_hash,))
            logger.debug(f"Invalidated cache for {query[:50]}...")
        else:
            conn.execute("DELETE FROM query_cache")
            logger.info("Cleared all cache")
        conn.commit()
        conn.close()

    def cleanup_expired(self):
        """Remove expired cache entries."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM query_cache WHERE expires_at <= datetime('now')")
        deleted = cursor.rowcount
        conn.commit()
        conn.close()
        if deleted > 0:
            logger.info(f"Cleaned up {deleted} expired cache entries")
