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

logger = logging.getLogger(__name__)

bp = Blueprint('rag', __name__, url_prefix='/api/v1/rag')

# Global ingestor instance
_ingestor: Optional[DocumentIngestor] = None


def get_ingestor() -> DocumentIngestor:
    """Get or create ingestor instance."""
    global _ingestor
    
    if _ingestor is None:
        import json
        
        # Load config
        config = {}
        try:
            with open('config/ingest_config.json', 'r') as f:
                config = json.load(f)
        except Exception:
            pass
        
        _ingestor = DocumentIngestor(
            chroma_dir=config.get('chroma', {}).get('path', 'data/rag/chroma/'),
            collection_name=config.get('chroma', {}).get('collection_name', 'medical_documents'),
            chunk_size=config.get('chunking', {}).get('chunk_size', 512),
            chunk_overlap=config.get('chunking', {}).get('chunk_overlap', 50),
        )
        
        # Initialize Chroma
        _ingestor._init_chroma()
    
    return _ingestor


@bp.route('/query', methods=['POST'])
def query():
    """
    Query RAG system with prompt.
    
    Request body:
        {
            "prompt": "What is the treatment protocol for X?",
            "n_results": 5,              // Optional, default 5
            "include_sources": true        // Optional
        }
    
    Response:
        {
            "answer": "Generated answer...",
            "sources": [
                {
                    "text": "...",
                    "source": "document.pdf",
                    "page": 3,
                    "section": "Treatment Protocol",
                    "relevance": 0.85
                }
            ]
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
    include_sources = data.get('include_sources', True)
    
    try:
        ingestor = get_ingestor()
        
        # Search for relevant documents
        results = ingestor.search(prompt, n_results=n_results)
        
        if not results:
            return jsonify({
                "answer": "No relevant documents found.",
                "sources": [],
                "message": "Try different query or ingest documents first"
            })
        
        # Build context from sources
        context_parts = []
        for r in results:
            meta = r.get('metadata', {})
            source = meta.get('source', 'unknown')
            page = meta.get('page')
            
            context_part = f"[{source}"
            if page:
                context_part += f", Page {page}"
            context_part += f"]\n{r['text']}\n"
            
            context_parts.append(context_part)
        
        context = "\n\n".join(context_parts)
        
        # Build RAG prompt
        rag_prompt = f"""Based on the following context, answer the question.

Context:
{context}

Question: {prompt}

Answer:"""
        
        # Generate answer using LLM
        from src.llm.server import LlamaCppServer, GenerationConfig
        
        try:
            # Load model path from config
            import json
            model_path = "data/models/Qwen3-8B-Q8_0.gguf"
            try:
                with open('config/llama_config.json', 'r') as f:
                    config = json.load(f)
                    model_path = config.get('model', {}).get('path', model_path)
            except Exception:
                pass
            
            server = LlamaCppServer(model_path=model_path)
            
            if server.load_model():
                result = server.generate(rag_prompt, GenerationConfig(
                    max_tokens=1024,
                    temperature=0.7,
                ))
                
                answer = result.text
            else:
                answer = "LLM not available for answer generation."
                
            server.shutdown()
            
        except Exception as e:
            logger.error(f"LLM generation failed: {e}")
            answer = "Answer generation failed. Sources retrieved but LLM unavailable."
        
        # Format response
        response = {
            "answer": answer,
            "sources": [
                {
                    "text": r['text'][:200] + "..." if len(r['text']) > 200 else r['text'],
                    "source": r['metadata'].get('source', 'unknown'),
                    "page": r['metadata'].get('page'),
                    "section": r['metadata'].get('section'),
                    "relevance": round(1 - r['distance'], 3) if 'distance' in r else None,
                }
                for r in results
            ] if include_sources else [],
        }
        
        return jsonify(response)
        
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
    
    Or JSON (file path):
        {
            "file_path": "path/to/document.pdf",
            "metadata": {"category": "protocol"}  // Optional
        }
    
    Response:
        {
            "status": "ingested",
            "source": "document.pdf",
            "chunks": 10,
            "duration_ms": 500.0
        }
    """
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
        ingestor = get_ingestor()
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