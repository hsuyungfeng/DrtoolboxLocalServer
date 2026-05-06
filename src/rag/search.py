"""
SemanticSearch - Semantic search interface for RAG.

This module provides a SemanticSearch class for performing vector-based
semantic search over Chroma collections.

Features:
- Semantic similarity search using Chroma
- Metadata filtering support
- Configurable top-k results
- Score normalization
"""

import os
import logging
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

# Chroma imports
try:
    import chromadb
    from chromadb.config import Settings
    CHROMA_AVAILABLE = True
except ImportError:
    CHROMA_AVAILABLE = False
    chromadb = None
    Settings = None

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    """Result of semantic search."""
    text: str
    id: str
    score: float
    distance: float
    metadata: Dict[str, Any]
    
    @property
    def similarity(self) -> float:
        """Convert distance to similarity score (0-1, higher is better)."""
        # Chroma uses cosine distance: 0 = identical, 2 = opposite
        # Convert to similarity: 1 - (distance / 2)
        return max(0.0, 1.0 - (self.distance / 2.0))


class SemanticSearch:
    """
    Semantic search interface for Chroma vector database.
    
    Performs vector similarity search over indexed documents
    with support for metadata filtering.
    
    Attributes:
        chroma_dir: Path to Chroma persistence directory
        collection_name: Name of Chroma collection to search
        default_top_k: Default number of results to return
    """
    
    def __init__(
        self,
        chroma_dir: str = "data/rag/chroma/",
        collection_name: str = "medical_documents",
        default_top_k: int = 5,
    ):
        """
        Initialize SemanticSearch.
        
        Args:
            chroma_dir: Path to Chroma persistence directory
            collection_name: Name of Chroma collection
            default_top_k: Default number of results to return
        """
        self.chroma_dir = chroma_dir
        self.collection_name = collection_name
        self.default_top_k = default_top_k
        
        self.client = None
        self.collection = None
        
        logger.info(f"SemanticSearch initialized: collection={collection_name}")
    
    def _init_client(self) -> bool:
        """Initialize Chroma client."""
        if not CHROMA_AVAILABLE:
            logger.error("chromadb not installed")
            return False
        
        try:
            os.makedirs(self.chroma_dir, exist_ok=True)
            
            self.client = chromadb.PersistentClient(
                path=self.chroma_dir,
                settings=Settings(
                    anonymized_telemetry=False,
                    allow_reset=False,
                )
            )
            
            # Get collection (must exist - use ingest.py to create)
            try:
                self.collection = self.client.get_collection(
                    name=self.collection_name
                )
            except Exception as e:
                logger.warning(f"Collection '{self.collection_name}' not found: {e}")
                return False
            
            logger.info(f"Connected to collection: {self.collection_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Chroma client: {e}")
            return False
    
    def search(
        self,
        query: str,
        top_k: Optional[int] = None,
        where: Optional[Dict[str, Any]] = None,
        where_document: Optional[Dict[str, Any]] = None,
        include_scores: bool = True,
    ) -> List[SearchResult]:
        """
        Perform semantic search.
        
        Args:
            query: Search query text
            top_k: Number of results to return (default: self.default_top_k)
            where: Optional metadata filter (Chroma where clause)
            where_document: Optional document content filter
            include_scores: Include similarity scores in results
            
        Returns:
            List of SearchResult objects sorted by similarity
            
        Raises:
            RuntimeError: If collection not initialized
        """
        if self.collection is None:
            if not self._init_client():
                raise RuntimeError(
                    f"Collection '{self.collection_name}' not found. "
                    f"Use DocumentIngestor to ingest documents first."
                )
        
        if top_k is None:
            top_k = self.default_top_k
        
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=top_k,
                where=where,
                where_document=where_document,
                include_embeddings=False,
                include_metadatas=True,
                include_distances=True,
            )
            
            # Parse results
            search_results = []
            
            if results.get('documents') and results['documents'][0]:
                for i, doc in enumerate(results['documents'][0]):
                    distance = results['distances'][0][i]
                    metadata = results['metadatas'][0][i]
                    doc_id = results['ids'][0][i]
                    
                    search_results.append(SearchResult(
                        text=doc,
                        id=doc_id,
                        score=0.0,  # Calculated below
                        distance=distance,
                        metadata=metadata,
                    ))
            
            # Sort by distance (lower is better) and calculate similarity
            search_results.sort(key=lambda x: x.distance)
            
            # Calculate similarity scores
            for result in search_results:
                result.score = result.similarity
            
            logger.info(f"Search returned {len(search_results)} results for query: {query[:50]}...")
            
            return search_results
            
        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise RuntimeError(f"Semantic search failed: {e}")
    
    def search_by_source(
        self,
        query: str,
        source_filter: str,
        top_k: Optional[int] = None,
    ) -> List[SearchResult]:
        """
        Search with source file filter.
        
        Args:
            query: Search query text
            source_filter: Source filename to filter by
            top_k: Number of results to return
            
        Returns:
            List of SearchResult from specified source
        """
        return self.search(
            query=query,
            top_k=top_k,
            where={"source": source_filter},
        )
    
    def get_collection_info(self) -> Dict[str, Any]:
        """Get collection information."""
        if self.collection is None:
            if not self._init_client():
                return {
                    "initialized": False,
                    "error": "Collection not found",
                }
        
        return {
            "initialized": True,
            "name": self.collection_name,
            "count": self.collection.count(),
            "chroma_dir": self.chroma_dir,
        }
    
    def __enter__(self):
        """Context manager entry."""
        self._init_client()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        pass