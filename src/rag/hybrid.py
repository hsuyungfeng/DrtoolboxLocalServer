"""
Hybrid Retriever module.
Combines sparse (SQLite FTS5 / n-gram) and dense (Chroma vector search)
retrieval results using Reciprocal Rank Fusion (RRF).
"""

import hashlib
import logging
from typing import List, Tuple, Dict, Any

logger = logging.getLogger(__name__)


def _key(text: str) -> str:
    """Generate a content hash key for deduplication and rank fusion."""
    return hashlib.md5(text.strip().encode("utf-8")).hexdigest()


def reciprocal_rank_fusion(
    sparse_ranked: List[Tuple[float, str]],
    dense_ranked: List[str],
    k: int = 60
) -> List[Tuple[str, str, float]]:
    """
    Perform Reciprocal Rank Fusion (RRF) on sparse and dense ranked lists.

    Args:
        sparse_ranked: List of (score, content) sorted by score descending.
        dense_ranked: List of content strings ranked by similarity.
        k: Smoothing constant (default 60).

    Returns:
        List of (key, content, fused_score) tuples sorted by fused score descending.
    """
    fused_scores: Dict[str, float] = {}
    content_map: Dict[str, str] = {}

    # Rank sparse results (1-based ranking)
    for rank, (_, text) in enumerate(sparse_ranked, start=1):
        key = _key(text)
        content_map[key] = text
        fused_scores[key] = fused_scores.get(key, 0.0) + (1.0 / (k + rank))

    # Rank dense results (1-based ranking)
    for rank, text in enumerate(dense_ranked, start=1):
        key = _key(text)
        content_map[key] = text
        fused_scores[key] = fused_scores.get(key, 0.0) + (1.0 / (k + rank))

    # Sort keys descending by fused score
    sorted_keys = sorted(fused_scores.keys(), key=lambda x: fused_scores[x], reverse=True)
    return [(k_id, content_map[k_id], fused_scores[k_id]) for k_id in sorted_keys]


class HybridRetriever:
    """
    Hybrid retriever combining SimpleIndex (sparse) and SemanticSearch (dense).
    """

    def __init__(self, sparse_index: Any, dense_search: Any, k: int = 60):
        self.sparse_index = sparse_index
        self.dense_search = dense_search
        self.k = k

    def get_scored_chunks(self, question: str) -> List[Tuple[str, str, float]]:
        """
        Retrieve chunks using hybrid search (sparse + dense + RRF).
        Falls back to sparse-only on any Chroma/dense exception (D-06).

        Args:
            question: Search query.

        Returns:
            List of (key, content, score) tuples.
        """
        # 1. Sparse retrieval
        try:
            sparse_ranked = self.sparse_index.get_scored_chunks(question)
            sparse_ranked.sort(reverse=True, key=lambda x: x[0])
        except Exception as e:
            logger.error(f"HybridRetriever: Sparse retrieval error: {e}")
            sparse_ranked = []

        # 2. Dense retrieval with defensive fallback
        try:
            dense_results = self.dense_search.search(question, top_k=10)
            dense_ranked = [r.text for r in dense_results] if dense_results else []
        except Exception as e:
            logger.error(
                f"HybridRetriever: Chroma dense search failed for category, falling back to sparse-only: {e}"
            )
            return [(_key(content), content, score) for score, content in sparse_ranked]

        # 3. Fuse results
        return reciprocal_rank_fusion(sparse_ranked, dense_ranked, k=self.k)
