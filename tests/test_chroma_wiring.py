import os
import sys
import shutil
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from src.rag.ingest import DocumentIngestor
from src.rag.search import SemanticSearch

def test_chroma_embedding_wiring():
    test_dir = "data/rag/chroma_test/"
    collection_name = "wiring_tracer"
    model_name = "BAAI/bge-small-zh-v1.5"

    # Clean up if existed
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir, ignore_errors=True)

    ingestor = DocumentIngestor(
        chroma_dir=test_dir,
        collection_name=collection_name,
        embedding_model=model_name
    )
    
    try:
        assert ingestor._init_chroma() is True
        assert ingestor.collection is not None

        # Add tracer document
        doc_text = "肉毒桿菌術後多久可以洗臉？"
        ingestor.collection.add(
            documents=[doc_text],
            ids=["tracer-1"]
        )

        # Query using SemanticSearch
        searcher = SemanticSearch(
            chroma_dir=test_dir,
            collection_name=collection_name,
            embedding_model=model_name
        )
        assert searcher._init_client() is True
        results = searcher.search("肉毒桿菌")

        assert len(results) > 0
        assert results[0].text == doc_text
        assert results[0].distance < 1.0
        assert results[0].similarity > 0.0

    finally:
        if os.path.exists(test_dir):
            shutil.rmtree(test_dir, ignore_errors=True)
