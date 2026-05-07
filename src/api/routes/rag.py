"""
RAG API routes for document query and search.

Endpoints:
- POST /api/v1/rag/query - Query RAG with prompt
- POST /api/v1/rag/search - Semantic search only
- POST /api/v1/rag/ingest - Ingest documents
- GET /api/v1/rag/collection - Collection info
"""

import logging
from flask import Blueprint, request, jsonify
from typing import Optional, List, Dict, Any

from src.rag.ingest import DocumentIngestor
from src.rag.query import QueryAnswer

logger = logging.getLogger(__name__)

bp = Blueprint('rag', __name__, url_prefix='/api/v1/rag')

# Global ingestor and query instances (now support dual collections)
_ingestors: Dict[str, DocumentIngestor] = {}
_query_answers: Dict[str, QueryAnswer] = {}
_config = {}


def load_config():
    """Load configuration from ingest_config.json."""
    global _config
    if not _config:
        import json
        try:
            with open('config/ingest_config.json', 'r') as f:
                _config = json.load(f)
        except Exception as e:
            logger.warning(f"Could not load config: {e}, using defaults")
            _config = {
                "chroma": {
                    "path": "data/rag/chroma_new/",
                    "collections": {
                        "general_medical": "general_medical",
                        "clinic_specific": "clinic_specific",
                    },
                    "default_collection": "general_medical",
                },
                "chunking": {"chunk_size": 512, "chunk_overlap": 50},
            }
    return _config


def get_ingestor(collection: str = "general_medical") -> DocumentIngestor:
    """Get or create ingestor instance for specified collection."""
    global _ingestors

    config = load_config()
    collections = config.get("chroma", {}).get("collections", {})
    collection_name = collections.get(collection, collection)

    if collection not in _ingestors:
        _ingestors[collection] = DocumentIngestor(
            chroma_dir=config.get("chroma", {}).get("path", "data/rag/chroma_new/"),
            collection_name=collection_name,
            chunk_size=config.get("chunking", {}).get("chunk_size", 512),
            chunk_overlap=config.get("chunking", {}).get("chunk_overlap", 50),
        )

        # Initialize Chroma
        _ingestors[collection]._init_chroma()

    return _ingestors[collection]


def get_query_answer(collection: str = "both") -> QueryAnswer:
    """Get or create QueryAnswer instance.

    Args:
        collection: "general_medical", "clinic_specific", or "both" (default: "both")
    """
    global _query_answers

    if collection not in _query_answers:
        config = load_config()
        chroma_path = config.get("chroma", {}).get("path", "data/rag/chroma_new/")

        if collection == "both":
            # Dual collection mode
            general_search = get_ingestor("general_medical").collection
            clinic_search = get_ingestor("clinic_specific").collection

            # Create general search instance
            from src.rag.search import SemanticSearch
            general = SemanticSearch(
                chroma_dir=chroma_path,
                collection_name="general_medical",
                default_top_k=5,
            )
            clinic = SemanticSearch(
                chroma_dir=chroma_path,
                collection_name="clinic_specific",
                default_top_k=5,
            )

            _query_answers[collection] = QueryAnswer(
                chroma_dir=chroma_path,
                collection_name="general_medical",
                top_k=5,
                clinic_search=clinic,
            )
        else:
            # Single collection mode
            collections = config.get("chroma", {}).get("collections", {})
            collection_name = collections.get(collection, collection)

            _query_answers[collection] = QueryAnswer(
                chroma_dir=chroma_path,
                collection_name=collection_name,
                top_k=5,
            )

    return _query_answers[collection]


@bp.route('/query', methods=['POST'])
def query():
    """
    Query RAG system with prompt (with confidence and citations).
    
    Request body:
        {
            "prompt": "What is the treatment protocol for X?",
            "n_results": 5              // Optional, default 5
        }
    
    Response (new format with citations):
        {
            "answer": "Generated answer...",
            "confidence": 0.85,
            "confidence_level": "high",
            "citations": [
                {
                    "document_name": "document.pdf",
                    "section_heading": "Treatment Protocol",
                    "page_number": 3,
                    "chunk_index": 0,
                    "ingestion_timestamp": "2026-05-06T12:00:00Z",
                    "text_snippet": "..."
                }
            ],
            "sources": ["document.pdf"],
            "query_time_ms": 150.0,
            "generation_time_ms": 250.0,
            "chunks_retrieved": 5
        }
    """
    data = request.get_json()

    if not data or 'prompt' not in data:
        return jsonify({
            "error": "Bad request",
            "message": "Missing required field: prompt"
        }), 400

    prompt = data['prompt']
    n_results = data.get('n_results', 5)
    collection = data.get('collection', 'both')  # 'general_medical', 'clinic_specific', or 'both'

    try:
        # Use QueryAnswer for proper confidence and citation handling
        qa = get_query_answer(collection=collection)
        
        # Get LLM server if available
        llm_server = None
        try:
            import requests
            # Use external llama-server for better performance (GPU-accelerated)
            response = requests.post(
                'http://127.0.0.1:8081/v1/chat/completions',
                json={
                    'messages': [
                        {'role': 'user', 'content': prompt}
                    ],
                    'max_tokens': 256,
                },
                timeout=30
            )
            if response.status_code == 200:
                result_data = response.json()
                # Extract content from llama-server response
                if result_data.get('choices'):
                    llm_response = result_data['choices'][0]['message']['content']
                    # Use LLM response directly, combined with RAG context
                    result = qa.query(prompt, top_k=n_results, use_llm=False)
                    result.answer = f"[Based on retrieved context]\n{result.answer}\n\n[LLM Enhancement]: {llm_response}"
                    return jsonify(result.to_dict())
            else:
                raise Exception(f"LLM server error: {response.status_code}")
        except Exception as e:
            logger.warning(f"Using RAG-only mode: {e}")
        
        # Execute RAG query
        result = qa.query(prompt, top_k=n_results, use_llm=False)
        
        # Return new format with confidence and citations
        return jsonify(result.to_dict())
        
    except Exception as e:
        logger.error(f"RAG query error: {e}")
        return jsonify({
            "error": "Query failed",
            "message": str(e),
        }), 500


@bp.route('/search', methods=['POST'])
def search():
    """
    Semantic search only (no LLM generation).
    
    Request body:
        {
            "query": "search terms",
            "n_results": 5    // Optional
        }
    
    Response:
        {
            "results": [...]
        }
    """
    data = request.get_json()
    
    if not data or 'query' not in data:
        return jsonify({
            "error": "Bad request",
            "message": "Missing required field: query"
        }), 400
    
    query = data['query']
    n_results = data.get('n_results', 5)
    
    try:
        ingestor = get_ingestor()
        results = ingestor.search(query, n_results=n_results)
        
        return jsonify({
            "results": [
                {
                    "text": r['text'],
                    "source": r['metadata'].get('source', 'unknown'),
                    "page": r['metadata'].get('page'),
                    "section": r['metadata'].get('section'),
                    "relevance": round(1 - r['distance'], 3) if 'distance' in r else None,
                }
                for r in results
            ],
            "count": len(results),
        })
        
    except Exception as e:
        logger.error(f"Search error: {e}")
        return jsonify({
            "error": "Search failed",
            "message": str(e),
        }), 500


@bp.route('/ingest', methods=['POST'])
def ingest():
    """
    Ingest document into RAG.

    Request body (multipart/form-data):
        file: Document file (PDF, DOCX, TXT)
        collection: Optional, "general_medical" or "clinic_specific" (default: "general_medical")

    Or JSON (file path):
        {
            "file_path": "path/to/document.pdf",
            "collection": "clinic_specific",  // Optional
            "metadata": {"category": "protocol"}  // Optional
        }

    Response:
        {
            "status": "ingested",
            "source": "document.pdf",
            "chunks": 10,
            "duration_ms": 500.0,
            "collection": "clinic_specific"
        }
    """
    # Get collection from request
    collection = request.form.get('collection', 'general_medical')
    if request.is_json:
        data = request.get_json()
        collection = data.get('collection', 'general_medical')

    # Check for file upload
    if 'file' in request.files:
        file = request.files['file']

        # Save to temp location
        import tempfile
        import os

        temp_dir = tempfile.mkdtemp()
        file_path = os.path.join(temp_dir, file.filename)
        file.save(file_path)
        
        metadata = {"filename": file.filename}
        
    elif request.is_json:
        data = request.get_json()
        file_path = data.get('file_path')
        
        if not file_path:
            return jsonify({
                "error": "Bad request",
                "message": "Missing file_path"
            }), 400
        
        metadata = data.get('metadata', {})
        
    else:
        return jsonify({
            "error": "Bad request",
            "message": "Provide file or file_path"
        }), 400
    
    try:
        ingestor = get_ingestor(collection=collection)
        result = ingestor.ingest(file_path, metadata)
        
        return jsonify({
            "status": "ingested",
            "source": os.path.basename(file_path),
            "chunks": result.chunks,
            "duration_ms": result.duration_ms,
            "collection": result.collection,
            "errors": result.errors,
        })
        
    except Exception as e:
        logger.error(f"Ingest error: {e}")
        return jsonify({
            "error": "Ingest failed",
            "message": str(e),
        }), 500


@bp.route('/collection', methods=['GET'])
def collection_info():
    """Get collection information."""
    try:
        ingestor = get_ingestor()
        info = ingestor.get_collection_info()
        
        return jsonify(info)
        
    except Exception as e:
        return jsonify({
            "error": "Collection info failed",
            "message": str(e),
        }), 500


@bp.route('/collection', methods=['DELETE'])
def delete_collection():
    """Delete collection (requires confirmation)."""
    data = request.get_json() or {}
    
    if not data.get('confirm'):
        return jsonify({
            "error": "Bad request",
            "message": "Must provide confirm=true"
        }), 400
    
    try:
        ingestor = get_ingestor()
        ingestor.delete_collection(confirm=True)
        
        return jsonify({
            "status": "deleted",
            "collection": ingestor.collection_name,
        })
        
    except Exception as e:
        return jsonify({
            "error": "Delete failed",
            "message": str(e),
        }), 500