"""
RAG Ingestion Dashboard API - Dual Collection Management

Endpoints:
- GET /api/v1/rag/dashboard/stats - Collection statistics
- POST /api/v1/rag/dashboard/upload - Upload document to collection
- DELETE /api/v1/rag/dashboard/document/<doc_id> - Delete document
- GET /api/v1/rag/dashboard/history - Ingestion history
- POST /api/v1/rag/dashboard/test-query - Test query against collection
"""

import os
import sys
import logging
import json
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template
from werkzeug.utils import secure_filename

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

logger = logging.getLogger(__name__)

rag_dashboard_bp = Blueprint('rag_dashboard', __name__)

# Configuration
ALLOWED_EXTENSIONS = {'txt', 'pdf', 'md', 'docx'}
MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB

# Ingestion history (in-memory for now, can be persisted to DB)
_ingestion_history = []


def allowed_file(filename):
    """Check if file extension is allowed."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@rag_dashboard_bp.route('/dashboard/rag', methods=['GET'])
def rag_dashboard_page():
    """Render RAG ingestion dashboard."""
    return render_template('rag_dashboard.html')


@rag_dashboard_bp.route('/api/v1/rag/dashboard/stats', methods=['GET'])
def get_collection_stats():
    """Get statistics for both collections."""
    try:
        from rag.ingest import DocumentIngestor

        collections_info = {}

        for collection in ['general_medical', 'clinic_specific']:
            try:
                ingestor = DocumentIngestor(
                    chroma_dir='data/rag/chroma/',
                    collection_name=collection,
                )
                ingestor._init_chroma()

                col = ingestor.collection
                count = col.count()

                collections_info[collection] = {
                    'name': collection,
                    'display_name': '通用醫療知識庫' if collection == 'general_medical' else '診所特定檔案',
                    'document_count': count,
                    'status': 'healthy' if count >= 0 else 'error'
                }
            except Exception as e:
                logger.warning(f"Error getting stats for {collection}: {e}")
                collections_info[collection] = {
                    'name': collection,
                    'display_name': '通用醫療知識庫' if collection == 'general_medical' else '診所特定檔案',
                    'document_count': 0,
                    'status': 'error'
                }

        return jsonify({
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'data': collections_info
        })

    except Exception as e:
        logger.error(f"Error getting collection stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@rag_dashboard_bp.route('/api/v1/rag/dashboard/upload', methods=['POST'])
def upload_document():
    """Upload document to specified collection."""
    try:
        if 'file' not in request.files:
            return jsonify({'success': False, 'error': 'No file provided'}), 400

        file = request.files['file']
        collection = request.form.get('collection', 'general_medical')

        if file.filename == '':
            return jsonify({'success': False, 'error': 'Empty filename'}), 400

        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': f'File type not allowed. Allowed: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400

        if file.content_length and file.content_length > MAX_FILE_SIZE:
            return jsonify({
                'success': False,
                'error': f'File too large. Max: {MAX_FILE_SIZE / 1024 / 1024}MB'
            }), 400

        # Validate collection
        if collection not in ['general_medical', 'clinic_specific']:
            return jsonify({
                'success': False,
                'error': 'Invalid collection'
            }), 400

        # Process file
        from rag.ingest import DocumentIngestor

        filename = secure_filename(file.filename)
        file_content = file.read().decode('utf-8', errors='ignore')

        ingestor = DocumentIngestor(
            chroma_dir='data/rag/chroma/',
            collection_name=collection,
        )

        result = ingestor.ingest_text(
            text=file_content,
            metadata={'source': filename, 'uploaded_at': datetime.utcnow().isoformat()}
        )

        # Record in history
        history_entry = {
            'timestamp': datetime.utcnow().isoformat(),
            'filename': filename,
            'collection': collection,
            'status': 'success',
            'chunks': len(result.get('chunks', []))
        }
        _ingestion_history.append(history_entry)

        logger.info(f"Uploaded {filename} to {collection}: {len(result.get('chunks', []))} chunks")

        return jsonify({
            'success': True,
            'message': f'Successfully uploaded {filename}',
            'chunks_created': len(result.get('chunks', [])),
            'collection': collection
        })

    except Exception as e:
        logger.error(f"Error uploading document: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@rag_dashboard_bp.route('/api/v1/rag/dashboard/history', methods=['GET'])
def get_ingestion_history():
    """Get ingestion history."""
    try:
        collection = request.args.get('collection')

        history = _ingestion_history
        if collection:
            history = [h for h in history if h['collection'] == collection]

        # Sort by timestamp descending
        history = sorted(history, key=lambda x: x['timestamp'], reverse=True)[:50]

        return jsonify({
            'success': True,
            'timestamp': datetime.utcnow().isoformat(),
            'data': history
        })

    except Exception as e:
        logger.error(f"Error getting ingestion history: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@rag_dashboard_bp.route('/api/v1/rag/dashboard/test-query', methods=['POST'])
def test_query():
    """Test semantic search against collection (without LLM inference)."""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        collection = data.get('collection', 'general_medical')

        if not query:
            return jsonify({'success': False, 'error': 'Query required'}), 400

        if collection not in ['general_medical', 'clinic_specific']:
            return jsonify({'success': False, 'error': 'Invalid collection'}), 400

        from rag.search import SemanticSearch

        # Use semantic search only (no LLM inference needed)
        search = SemanticSearch(
            chroma_dir='data/rag/chroma/',
            collection_name=collection,
            default_top_k=3
        )

        results = search.search(query)

        # Format results as citations (handle SearchResult objects)
        citations = []
        for r in results[:3]:
            try:
                # Try as object first
                source = getattr(r, 'metadata', {}).get('source', 'Unknown') if hasattr(r, 'metadata') else 'Unknown'
            except:
                # Fall back to dict access
                source = r.get('metadata', {}).get('source', 'Unknown') if isinstance(r, dict) else 'Unknown'
            citations.append(source)

        return jsonify({
            'success': True,
            'answer': 'Top relevant documents found',
            'citations': citations,
            'confidence': 0.8 if results else 0.0,
            'query': query,
            'collection': collection,
            'results_count': len(results)
        })

    except Exception as e:
        logger.error(f"Error testing query: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
