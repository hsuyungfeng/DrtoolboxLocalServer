"""Tests for HIS connection, queue, and cache layers."""

import pytest
import tempfile
import sqlite3
from src.db.his_connection import HISConnection, HISQueryError
from src.db.query_queue import QueryQueue, QueryTask
from src.db.query_cache import QueryCache


@pytest.fixture
def test_db():
    """Create temporary HIS test database."""
    fd, path = tempfile.mkstemp(suffix=".db")
    conn = sqlite3.connect(path)
    conn.execute("""
        CREATE TABLE patients (
            patient_id TEXT PRIMARY KEY,
            name TEXT,
            dob TEXT
        )
    """)
    conn.execute("INSERT INTO patients VALUES ('TEST_001', 'Test Patient', '1990-01-01')")
    conn.commit()
    conn.close()
    yield path
    import os
    os.close(fd)
    os.unlink(path)


def test_his_connection_read_only(test_db):
    """Test that read-only mode is enforced."""
    his = HISConnection(db_path=test_db)
    with pytest.raises(HISQueryError):
        his.execute("INSERT INTO patients VALUES ('TEST_002', 'Bad', '2000-01-01')")


def test_his_connection_select(test_db):
    """Test SELECT query execution."""
    his = HISConnection(db_path=test_db)
    result = his.execute("SELECT * FROM patients WHERE patient_id = ?", ("TEST_001",))
    assert len(result) == 1
    assert result[0]["name"] == "Test Patient"


def test_query_queue_submit():
    """Test query queue submission."""
    from src.db.query_queue import set_query_queue
    queue = QueryQueue()
    set_query_queue(queue)
    
    task = QueryTask(query="SELECT 1", params=())
    task_id = queue.submit(task)
    assert task_id is not None


def test_query_cache_hit_miss(test_db):
    """Test cache hit and miss."""
    fd, cache_db = tempfile.mkstemp(suffix=".db")
    cache = QueryCache(db_path=cache_db)
    
    query = "SELECT * FROM patients"
    result = [{"patient_id": "TEST_001", "name": "Test"}]
    
    cached = cache.get(query, ())
    assert cached is None
    
    cache.set(query, (), result)
    cached = cache.get(query, ())
    assert cached == result
    
    import os
    os.close(fd)
    os.unlink(cache_db)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
