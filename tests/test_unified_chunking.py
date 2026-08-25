import os
import sys
import shutil
import sqlite3
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from src.rag_engine import RAGEngine, SimpleIndex
from src.rag.ingest import DocumentIngestor


@pytest.fixture
def temp_env(tmp_path):
    db_path = str(tmp_path / "rag.db")
    chroma_dir = str(tmp_path / "chroma")
    return db_path, chroma_dir


def test_simple_index_chunk_id_with_chunker(temp_env):
    _, chroma_dir = temp_env
    
    # Init DB schema
    engine = RAGEngine()
    db_path = engine.db_path
    
    ingestor = DocumentIngestor(
        chroma_dir=chroma_dir,
        collection_name="test_general",
        embedding_model="BAAI/bge-small-zh-v1.5"
    )
    ingestor._init_chroma()
    
    index = SimpleIndex(reasoner=None, category="general", db_path=db_path, chunker=ingestor)
    
    doc = {
        "id": "data/documents/general/test_doc.txt",
        "content": "肉毒桿菌素（Botulinum Toxin）是一種神經毒素蛋白。" * 30
    }
    
    index.add_document(doc)
    
    # Verify rows in SQLite
    conn = sqlite3.connect(db_path)
    rows = conn.execute("SELECT chunk_id, chunk_index, content FROM rag_chunks WHERE doc_id = ?", (doc["id"],)).fetchall()
    conn.close()
    
    assert len(rows) > 0
    for chunk_id, idx, content in rows:
        assert chunk_id is not None
        assert len(chunk_id) > 0
        
    # Verify deterministic chunk_id matches chunker directly
    expected_chunks = ingestor.chunk_text(doc["content"], doc["id"])
    assert [r[0] for r in rows] == [c.chunk_id for c in expected_chunks]


def test_idempotent_ingest_general(temp_env):
    engine = RAGEngine()
    
    doc = {
        "id": "data/documents/general/test_idem.txt",
        "content": "玻尿酸注射後的注意事項包含避免按壓與高溫環境。" * 10
    }
    
    # Ingest once
    engine.ingest_general_data([doc])
    
    conn = sqlite3.connect(engine.db_path)
    hash_count_1 = conn.execute("SELECT COUNT(*) FROM rag_doc_hashes WHERE doc_id = ?", (doc["id"],)).fetchone()[0]
    chunks_count_1 = conn.execute("SELECT COUNT(*) FROM rag_chunks WHERE doc_id = ?", (doc["id"],)).fetchone()[0]
    conn.close()
    
    assert hash_count_1 == 1
    assert chunks_count_1 > 0
    
    # Ingest second time (unchanged)
    engine.ingest_general_data([doc])
    
    conn = sqlite3.connect(engine.db_path)
    hash_count_2 = conn.execute("SELECT COUNT(*) FROM rag_doc_hashes WHERE doc_id = ?", (doc["id"],)).fetchone()[0]
    chunks_count_2 = conn.execute("SELECT COUNT(*) FROM rag_chunks WHERE doc_id = ?", (doc["id"],)).fetchone()[0]
    conn.close()
    
    assert hash_count_2 == hash_count_1
    assert chunks_count_2 == chunks_count_1


def test_changed_content_reingest(temp_env):
    engine = RAGEngine()
    
    doc_initial = {
        "id": "data/documents/general/test_update.txt",
        "content": "初始版本內容：音波拉皮術後保養。"
    }
    engine.ingest_general_data([doc_initial])
    
    conn = sqlite3.connect(engine.db_path)
    hash_1 = conn.execute("SELECT content_hash FROM rag_doc_hashes WHERE doc_id = ?", (doc_initial["id"],)).fetchone()[0]
    conn.close()
    
    # Update content
    doc_updated = {
        "id": "data/documents/general/test_update.txt",
        "content": "更新版本內容：音波拉皮與電波拉皮術後保養原則。" * 5
    }
    engine.ingest_general_data([doc_updated])
    
    conn = sqlite3.connect(engine.db_path)
    hash_2 = conn.execute("SELECT content_hash FROM rag_doc_hashes WHERE doc_id = ?", (doc_updated["id"],)).fetchone()[0]
    conn.close()
    
    assert hash_1 != hash_2
