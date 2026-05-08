"""
HIS Database Connection Layer

Provides read-only access to clinic HIS database with connection pooling,
timeout handling, and error management per D-01 architecture decision.
"""

import os
import sqlite3
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from threading import Lock
import queue
import time

logger = logging.getLogger(__name__)


class HISConnectionError(Exception):
    """Raised when HIS connection fails."""
    pass


class HISQueryTimeoutError(Exception):
    """Raised when HIS query exceeds timeout."""
    pass


class HISQueryError(Exception):
    """Raised when HIS query is invalid or returns error."""
    pass


@dataclass
class HISConfig:
    """HIS database configuration from environment."""
    db_type: str = "sqlite"
    db_path: Optional[str] = None
    db_host: Optional[str] = None
    db_port: int = 3306
    db_user: Optional[str] = None
    db_password: Optional[str] = None
    query_timeout: int = 5
    pool_min_size: int = 5
    pool_max_size: int = 10

    @staticmethod
    def from_env() -> "HISConfig":
        """Load HIS config from environment variables."""
        return HISConfig(
            db_type=os.getenv("HIS_DB_TYPE", "sqlite"),
            db_path=os.getenv("HIS_DB_PATH"),
            db_host=os.getenv("HIS_DB_HOST"),
            db_port=int(os.getenv("HIS_DB_PORT", "3306")),
            db_user=os.getenv("HIS_DB_USER"),
            db_password=os.getenv("HIS_DB_PASSWORD"),
            query_timeout=int(os.getenv("HIS_QUERY_TIMEOUT", "5")),
            pool_min_size=int(os.getenv("HIS_POOL_MIN", "5")),
            pool_max_size=int(os.getenv("HIS_POOL_MAX", "10")),
        )


class ConnectionPool:
    """Thread-safe connection pool for HIS database."""

    def __init__(self, config: HISConfig):
        self.config = config
        self.pool: queue.Queue = queue.Queue(maxsize=config.pool_max_size)
        self.lock = Lock()
        self.created_count = 0
        self._initialize_pool()

    def _initialize_pool(self):
        """Pre-populate pool with min_size connections."""
        for _ in range(self.config.pool_min_size):
            try:
                conn = self._create_connection()
                self.pool.put(conn, block=False)
                self.created_count += 1
            except Exception as e:
                logger.warning(f"Failed to create initial connection: {e}")

    def _create_connection(self):
        """Create a new database connection."""
        if self.config.db_type == "sqlite":
            if not self.config.db_path:
                raise HISConnectionError("HIS_DB_PATH required for SQLite")
            conn = sqlite3.connect(self.config.db_path, timeout=self.config.query_timeout)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA query_only = ON")
            logger.info(f"Created SQLite connection to {self.config.db_path}")
            return conn
        else:
            raise HISConnectionError(f"Unsupported db_type: {self.config.db_type}")

    def get_connection(self, timeout: float = 1.0):
        """Get a connection from the pool, creating if necessary."""
        try:
            return self.pool.get(timeout=timeout)
        except queue.Empty:
            if self.created_count < self.config.pool_max_size:
                with self.lock:
                    if self.created_count < self.config.pool_max_size:
                        conn = self._create_connection()
                        self.created_count += 1
                        return conn
            raise HISConnectionError("Connection pool exhausted")

    def return_connection(self, conn):
        """Return a connection to the pool."""
        try:
            self.pool.put(conn, block=False)
        except queue.Full:
            conn.close()

    def close_all(self):
        """Close all connections in pool."""
        while not self.pool.empty():
            try:
                conn = self.pool.get_nowait()
                conn.close()
            except queue.Empty:
                break


class HISConnection:
    """Read-only HIS database connection with pooling and timeout."""

    def __init__(
        self,
        db_path: Optional[str] = None,
        db_type: str = "sqlite",
        host: Optional[str] = None,
        port: int = 3306,
        user: Optional[str] = None,
        password: Optional[str] = None,
        query_timeout: int = 5,
    ):
        """Initialize HIS connection with environment fallback."""
        self.config = HISConfig(
            db_type=db_type or os.getenv("HIS_DB_TYPE", "sqlite"),
            db_path=db_path or os.getenv("HIS_DB_PATH"),
            db_host=host or os.getenv("HIS_DB_HOST"),
            db_port=port,
            db_user=user or os.getenv("HIS_DB_USER"),
            db_password=password or os.getenv("HIS_DB_PASSWORD"),
            query_timeout=query_timeout,
        )
        self.pool = ConnectionPool(self.config)
        logger.info(f"HISConnection initialized with db_type={self.config.db_type}")

    def execute(self, query: str, params: tuple = ()) -> List[Dict[str, Any]]:
        """Execute read-only SELECT query with timeout, return list of dicts."""
        if not query.strip().upper().startswith("SELECT"):
            raise HISQueryError("Only SELECT queries allowed (read-only mode)")

        conn = None
        try:
            conn = self.pool.get_connection()
            start_time = time.time()
            cursor = conn.cursor()
            cursor.execute(query, params)
            rows = cursor.fetchall()
            result = [dict(row) for row in rows]

            elapsed = time.time() - start_time
            if elapsed > self.config.query_timeout:
                logger.warning(f"Query took {elapsed:.2f}s (timeout: {self.config.query_timeout}s)")

            logger.debug(f"Query executed in {elapsed:.3f}s, returned {len(result)} rows")
            return result

        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) or "timeout" in str(e).lower():
                raise HISQueryTimeoutError(f"Query timeout or database locked: {e}")
            raise HISQueryError(f"Query error: {e}")
        except Exception as e:
            if "timeout" in str(e).lower():
                raise HISQueryTimeoutError(f"Query timeout: {e}")
            raise HISConnectionError(f"Connection error: {e}")
        finally:
            if conn:
                self.pool.return_connection(conn)

    def close(self):
        """Close all pooled connections."""
        self.pool.close_all()
        logger.info("HIS connection pool closed")


# Singleton instance
_his_connection: Optional[HISConnection] = None
_his_lock = Lock()


def get_his_connection() -> HISConnection:
    """Get or create singleton HISConnection."""
    global _his_connection
    if _his_connection is None:
        with _his_lock:
            if _his_connection is None:
                _his_connection = HISConnection()
    return _his_connection


def set_his_connection(conn: Optional[HISConnection]):
    """Set or reset the singleton connection (for testing)."""
    global _his_connection
    _his_connection = conn
