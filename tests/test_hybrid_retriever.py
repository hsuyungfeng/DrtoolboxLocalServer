import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))

from src.rag.hybrid import reciprocal_rank_fusion, HybridRetriever

class DummySparseIndex:
    def __init__(self, chunks=None):
        self.chunks = chunks or []

    def get_scored_chunks(self, question: str):
        return list(self.chunks)


class DummyDenseResult:
    def __init__(self, text: str):
        self.text = text


class DummyDenseSearch:
    def __init__(self, texts=None):
        self.texts = texts or []

    def search(self, question: str, top_k: int = 10):
        return [DummyDenseResult(t) for t in self.texts]


class RaisingDenseSearch:
    def __init__(self, exc_type=RuntimeError):
        self.exc_type = exc_type

    def search(self, question: str, top_k: int = 10):
        raise self.exc_type("Simulated dense search error")


def test_rrf_overlap_boost():
    # chunk B is present in both sparse & dense -> should rank first
    sparse = [(10.0, "chunk A"), (8.0, "chunk B")]
    dense = ["chunk B", "chunk C"]

    fused = reciprocal_rank_fusion(sparse, dense, k=60)
    assert fused[0][1] == "chunk B"
    assert {item[1] for item in fused} == {"chunk A", "chunk B", "chunk C"}


def test_rrf_empty_dense_degrades_to_sparse():
    sparse = [(10.0, "chunk 1"), (5.0, "chunk 2"), (2.0, "chunk 3")]
    dense = []

    fused = reciprocal_rank_fusion(sparse, dense, k=60)
    assert [item[1] for item in fused] == ["chunk 1", "chunk 2", "chunk 3"]


def test_hybrid_retriever_normal_flow():
    sparse_index = DummySparseIndex([(1.0, "chunk A"), (0.5, "chunk B")])
    dense_search = DummyDenseSearch(["chunk B", "chunk C"])
    retriever = HybridRetriever(sparse_index, dense_search, k=60)

    fused = retriever.get_scored_chunks("query")
    assert fused[0][1] == "chunk B"
    contents = [item[1] for item in fused]
    assert "chunk A" in contents
    assert "chunk C" in contents


def test_hybrid_retriever_runtime_error_fallback():
    sparse_index = DummySparseIndex([(5.0, "sparse 1"), (10.0, "sparse 2")])
    dense_search = RaisingDenseSearch(RuntimeError)
    retriever = HybridRetriever(sparse_index, dense_search, k=60)

    fused = retriever.get_scored_chunks("query")
    assert [item[1] for item in fused] == ["sparse 2", "sparse 1"]


def test_hybrid_retriever_generic_exception_fallback():
    sparse_index = DummySparseIndex([(2.0, "sparse A"), (4.0, "sparse B")])
    dense_search = RaisingDenseSearch(Exception)
    retriever = HybridRetriever(sparse_index, dense_search, k=60)

    fused = retriever.get_scored_chunks("query")
    assert [item[1] for item in fused] == ["sparse B", "sparse A"]
