"""
QueryAnswer - RAG query and answer generation.

This module provides a QueryAnswer class for:
- Retrieving context from semantic search
- Generating answers using LLM
- Calculating confidence scores
- Formatting source citations

Features:
- Confidence score calculation (high/medium/low)
- Full citation tracking (filename, section, page)
- Integration with LlamaCppServer for generation
"""

import time
import logging
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass, field

from .search import SemanticSearch, SearchResult, search_dual

logger = logging.getLogger(__name__)


@dataclass
class Citation:
    """Source citation for answer."""
    document_name: str
    section_heading: Optional[str] = None
    page_number: Optional[int] = None
    chunk_index: Optional[int] = None
    ingestion_timestamp: Optional[str] = None
    text_snippet: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "document_name": self.document_name,
            "section_heading": self.section_heading,
            "page_number": self.page_number,
            "chunk_index": self.chunk_index,
            "ingestion_timestamp": self.ingestion_timestamp,
            "text_snippet": self.text_snippet,
        }


@dataclass
class AnswerResult:
    """Result of RAG query answer generation."""
    answer: str
    confidence: float
    confidence_level: str  # "high", "medium", "low"
    citations: List[Citation] = field(default_factory=list)
    sources: List[str] = field(default_factory=list)
    query_time_ms: float = 0.0
    generation_time_ms: float = 0.0
    chunks_retrieved: int = 0
    old_documents_warning: Optional[List[Dict[str, Any]]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to API response format."""
        return {
            "answer": self.answer,
            "confidence": self.confidence,
            "confidence_level": self.confidence_level,
            "citations": [c.to_dict() for c in self.citations],
            "sources": self.sources,
            "query_time_ms": self.query_time_ms,
            "generation_time_ms": self.generation_time_ms,
            "chunks_retrieved": self.chunks_retrieved,
            "old_documents_warning": self.old_documents_warning,
        }


class QueryAnswer:
    """
    RAG query answering system.
    
    Combines semantic search with LLM generation to produce
    grounded answers with source citations.
    
    Attributes:
        search: SemanticSearch instance
        llm_server: Optional LlamaCppServer for generation
        top_k: Number of chunks to retrieve
        confidence_thresholds: Thresholds for high/medium/low
    """
    
    def __init__(
        self,
        chroma_dir: str = "data/rag/chroma_new/",
        collection_name: str = "medical_documents",
        llm_server=None,  # Optional LlamaCppServer instance
        top_k: int = 5,
        confidence_thresholds: Tuple[float, float] = (0.7, 0.4),
        clinic_search: Optional[SemanticSearch] = None,  # For dual-collection mode
    ):
        """
        Initialize QueryAnswer.

        Args:
            chroma_dir: Path to Chroma directory
            collection_name: Name of Chroma collection
            llm_server: Optional LlamaCppServer for LLM generation
            top_k: Number of context chunks to retrieve
            confidence_thresholds: (high_threshold, medium_threshold)
            clinic_search: Optional SemanticSearch for clinic_specific collection (enables dual mode)
        """
        self.search = SemanticSearch(
            chroma_dir=chroma_dir,
            collection_name=collection_name,
            default_top_k=top_k,
        )
        self.clinic_search = clinic_search  # None = single collection mode, set = dual mode
        self.llm_server = llm_server
        self.top_k = top_k
        self.high_threshold, self.medium_threshold = confidence_thresholds

        mode = "dual" if clinic_search else "single"
        logger.info(f"QueryAnswer initialized: mode={mode}, top_k={top_k}")
    
    def retrieve_context(
        self,
        query: str,
        top_k: Optional[int] = None,
    ) -> List[SearchResult]:
        """
        Retrieve relevant context chunks.

        In dual mode, searches both general_medical and clinic_specific collections.
        In single mode, searches only the configured collection.

        Args:
            query: User query
            top_k: Number of chunks to retrieve

        Returns:
            List of SearchResult with relevant context
        """
        if top_k is None:
            top_k = self.top_k

        try:
            # Use dual search if clinic_search is available
            if self.clinic_search:
                results = search_dual(
                    query_text=query,
                    general_search=self.search,
                    clinic_search=self.clinic_search,
                    top_k=top_k,
                )
            else:
                results = self.search.search(query=query, top_k=top_k)

            logger.info(f"Retrieved {len(results)} context chunks")
            return results

        except Exception as e:
            logger.error(f"Context retrieval failed: {e}")
            raise
    
    def calculate_confidence(
        self,
        search_results: List[SearchResult],
    ) -> Tuple[float, str, Dict[str, Any]]:
        """
        Calculate confidence score from search results.
        
        Args:
            search_results: List of SearchResult from semantic search
            
        Returns:
            Tuple of (confidence_score, confidence_level, warnings)
        """
        warnings = []
        
        if not search_results:
            return 0.0, "low", {"old_documents": []}
        
        # Check document age
        old_documents = []
        current_time = time.time()
        ONE_YEAR_SECONDS = 365 * 24 * 60 * 60
        
        for result in search_results:
            meta = result.metadata or {}
            ingested_at = meta.get("ingested_at", "")
            if ingested_at:
                try:
                    doc_time = int(ingested_at)
                    age_seconds = current_time - doc_time
                    if age_seconds > ONE_YEAR_SECONDS:
                        old_documents.append({
                            "document": meta.get("source", "unknown"),
                            "age_years": round(age_seconds / ONE_YEAR_SECONDS, 1)
                        })
                except (ValueError, TypeError):
                    pass
        
        if old_documents:
            warnings.append({
                "type": "old_documents",
                "message": f"{len(old_documents)} document(s) over 1 year old - verify information",
                "documents": old_documents
            })
        
        # Use average of top results' similarities
        top_results = search_results[:3]  # Top 3
        avg_similarity = sum(r.similarity for r in top_results) / len(top_results)
        
        # Adjust confidence for old documents
        if old_documents:
            avg_similarity *= 0.8  # Reduce confidence by 20% for old docs
            logger.warning(f"Confidence reduced by 20% due to {len(old_documents)} old document(s)")
        
        # Determine confidence level
        if avg_similarity >= self.high_threshold:
            level = "high"
        elif avg_similarity >= self.medium_threshold:
            level = "medium"
        else:
            level = "low"
        
        logger.debug(f"Confidence: {avg_similarity:.3f} ({level})")
        
        return round(avg_similarity, 3), level, {"old_documents": old_documents, "warnings": warnings}
    
    def format_citations(
        self,
        search_results: List[SearchResult],
        max_snippet_len: int = 200,
    ) -> List[Citation]:
        """
        Format source citations from search results.
        
        Args:
            search_results: List of SearchResult
            max_snippet_len: Maximum length of text snippet
            
        Returns:
            List of Citation objects
        """
        citations = []
        seen_docs = set()  # Avoid duplicates
        
        for result in search_results:
            metadata = result.metadata
            source = metadata.get("source", "unknown")
            
            # Skip duplicate sources (keep first occurrence)
            if source in seen_docs:
                continue
            seen_docs.add(source)
            
            # Format timestamp if available
            timestamp = None
            if metadata.get("ingested_at"):
                try:
                    timestamp = time.strftime(
                        "%Y-%m-%dT%H:%M:%SZ",
                        time.gmtime(metadata["ingested_at"])
                    )
                except Exception:
                    pass
            
            # Truncate snippet
            snippet = result.text[:max_snippet_len]
            if len(result.text) > max_snippet_len:
                snippet += "..."
            
            citation = Citation(
                document_name=source,
                section_heading=metadata.get("section"),
                page_number=metadata.get("page"),
                chunk_index=metadata.get("chunk_index"),
                ingestion_timestamp=timestamp,
                text_snippet=snippet,
            )
            
            citations.append(citation)
        
        return citations
    
    def generate_answer(
        self,
        query: str,
        context_chunks: List[SearchResult],
        use_llm: bool = True,
        old_docs_warning: Optional[List[Dict[str, Any]]] = None,
    ) -> str:
        """
        Generate answer from context chunks.
        
        Args:
            query: User query
            context_chunks: Retrieved context
            use_llm: Whether to use LLM for generation
            
        Returns:
            Generated answer text
        """
        import re
        
        # Build prompt with context, deterministically redacting prices
        redacted_chunks = []
        
        for chunk in context_chunks:
            text = chunk.text
            
            # Strict Policy: Unconditionally redact all prices UNLESS explicitly marked with valid_until
            is_valid = False
            if chunk.metadata and "valid_until" in chunk.metadata:
                try:
                    import time
                    valid_date = time.strptime(chunk.metadata["valid_until"], "%Y-%m-%d")
                    if valid_date >= time.localtime():
                        is_valid = True
                except Exception:
                    pass
                    
            if not is_valid:
                # Forcefully redact all prices and potential price formats
                text = re.sub(r'\$\s*\d+(?:,\d+)*', '[請致電診所確認]', text)
                text = re.sub(r'\d+(?:,\d+)*\s*[元塊]', '[請致電診所確認]', text)
                text = re.sub(r'(?:價格|售價|特價|優惠價|費用|價值)[\s:：]*\d+(?:,\d+)*', '價格[請致電診所確認]', text)
                text = re.sub(r'\d+\s*[堂次管]\s*/\s*[$]?\s*\d+(?:,\d+)*', '[請致電診所確認]', text)
                
                # Catch standalone large numbers (>=1000) that aren't years (202x, 11x)
                text = re.sub(r'(?<!\d)(?!(?:202\d|11\d)\b)[1-9]\d{3,7}(?!\d)', '[請致電診所確認]', text)
                text = re.sub(r'(?<!\d)[1-9]\d{0,2}(?:,\d{3})+(?!\d)', '[請致電診所確認]', text)
                
                # Catch CC/price, U/price, 瓶/price
                text = re.sub(r'(?:CC|U|瓶|堂|次)[\s/]+\d+(?:,\d+)*', ' [請致電診所確認]', text, flags=re.IGNORECASE)

            redacted_chunks.append(text)

        if not use_llm or self.llm_server is None:
            # Simple concatenation fallback
            context_text = "\n\n".join(
                f"[Context {i+1}]\n{text}"
                for i, text in enumerate(redacted_chunks)
            )
            return f"Based on the retrieved context:\n\n{context_text[:1000]}..."
            
        context_text = "\n\n".join(
            f"Source {i+1}: {text}"
            for i, text in enumerate(redacted_chunks)
        )
        
        from datetime import datetime
        current_date = datetime.now().strftime("%Y-%m-%d")
        
        warning_text = ""
        if old_docs_warning:
            warning_text = "\n[CRITICAL SYSTEM WARNING]: The retrieved documents are OVER 1 YEAR OLD and have EXPIRED. You MUST NOT quote any prices, activities, or promotions from them. Tell the user the activity has likely expired and they should consult the staff.\n"

        prompt = f"""Based on the following context, answer the question concisely and accurately.
You must ALWAYS answer in Traditional Chinese (繁體中文).
You represent 緻妍 (Zhiyan Aesthetic Clinic). If the context mentions "樹義美醫中心" or "Drtoolbox", you must treat it as and refer to it as "緻妍". Do NEVER use the old names.
{warning_text}
Today's Date: {current_date}

Context:
{context_text}

Question: {query}

CRITICAL PRICING & ACTIVITY RULES (MUST FOLLOW):
1. Look for a specific, unexpired validity date in the Context.
2. If there is NO explicit valid expiration date, or if it is expired, YOU ARE STRICTLY FORBIDDEN from outputting ANY prices (e.g. $8000, 60000), cost amounts, or specific package combinations.
3. If it lacks a clear date, DO NOT summarize the packages. Instead, you MUST ONLY reply with: "目前無法確認該活動的時效與具體內容，為避免提供錯誤資訊，建議您致電診所向專人諮詢以獲取最準確的報價喔！"

Answer:"""
        
        try:
            result = self.llm_server.generate(prompt)
            return result.text.strip()
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            # Fallback to concatenation
            return f"Based on retrieved context: {context_chunks[0].text[:300]}..."
    
    def query(
        self,
        query: str,
        top_k: Optional[int] = None,
        use_llm: bool = True,
    ) -> AnswerResult:
        """
        Process a RAG query end-to-end.
        
        Args:
            query: User question
            top_k: Number of context chunks
            use_llm: Use LLM for generation
            
        Returns:
            AnswerResult with answer, confidence, citations
        """
        total_start = time.time()
        
        # Step 1: Retrieve context
        query_start = time.time()
        context_chunks = self.retrieve_context(query, top_k)
        query_time_ms = (time.time() - query_start) * 1000
        
        if not context_chunks:
            return AnswerResult(
                answer="No relevant context found. Please try a different query or ingest documents first.",
                confidence=0.0,
                confidence_level="low",
                citations=[],
                query_time_ms=query_time_ms,
                generation_time_ms=0.0,
                chunks_retrieved=0,
                old_documents_warning=[],
            )
        
        # Step 2: Calculate confidence (includes age warnings)
        confidence, level, age_warnings = self.calculate_confidence(context_chunks)
        
        # Check for old document warnings
        old_docs_warning = None
        if age_warnings and age_warnings.get("old_documents"):
            old_docs_warning = age_warnings["old_documents"]
        
        # Step 3: Format citations
        citations = self.format_citations(context_chunks)
        sources = list(set(c.document_name for c in citations))
        
        # Step 4: Generate answer
        gen_start = time.time()
        answer = self.generate_answer(query, context_chunks, use_llm, old_docs_warning)
        gen_time_ms = (time.time() - gen_start) * 1000
        
        total_time_ms = (time.time() - total_start) * 1000
        
        logger.info(
            f"Query processed: confidence={confidence:.3f} ({level}), "
            f"chunks={len(context_chunks)}, time={total_time_ms:.0f}ms"
        )
        
        return AnswerResult(
            answer=answer,
            confidence=confidence,
            confidence_level=level,
            citations=citations,
            sources=sources,
            query_time_ms=query_time_ms,
            generation_time_ms=gen_time_ms,
            chunks_retrieved=len(context_chunks),
            old_documents_warning=old_docs_warning or [],
        )
    
    def query_with_llm(
        self,
        query: str,
        llm_server,  # Must provide LlamaCppServer instance
        top_k: Optional[int] = None,
    ) -> AnswerResult:
        """
        Query with explicit LLM server.
        
        Args:
            query: User question
            llm_server: LlamaCppServer instance
            top_k: Number of context chunks
            
        Returns:
            AnswerResult
        """
        original_server = self.llm_server
        self.llm_server = llm_server
        
        try:
            return self.query(query, top_k, use_llm=True)
        finally:
            self.llm_server = original_server