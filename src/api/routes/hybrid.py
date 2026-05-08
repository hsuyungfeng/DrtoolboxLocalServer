"""
Hybrid Query API routes combining SQLite Database + RAG Search.

Endpoints:
- POST /api/v1/hybrid/query - Intelligent query routing
- GET  /api/v1/hybrid/clinic/schedule - Clinic schedule (DB)
- GET  /api/v1/hybrid/clinic/staff - Staff roster (DB)
- GET  /api/v1/hybrid/clinic/supplies - Inventory status (DB)
- POST /api/v1/hybrid/medical/search - Medical knowledge (RAG)
- POST /api/v1/hybrid/medical/condition - Condition lookup (DB)
- POST /api/v1/hybrid/diagnostic - Diagnostic query (Hybrid)
"""

import logging
import sys
import os
from pathlib import Path
from flask import Blueprint, request, jsonify
from typing import Optional, Dict, Any
import json

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))

from scripts.hybrid_query import HybridQueryEngine

logger = logging.getLogger(__name__)

bp = Blueprint('hybrid', __name__, url_prefix='/api/v1/hybrid')

# Global hybrid query engine instance
_engine: Optional[HybridQueryEngine] = None


def get_engine() -> HybridQueryEngine:
    """Get or create hybrid query engine instance."""
    global _engine

    if _engine is None:
        try:
            _engine = HybridQueryEngine()
            logger.info("✓ Hybrid query engine initialized")
        except Exception as e:
            logger.error(f"Failed to initialize hybrid engine: {e}")
            raise

    return _engine


# ============================================================================
# CLINIC OPERATIONS (Database Queries)
# ============================================================================

@bp.route('/clinic/schedule', methods=['GET'])
def get_clinic_schedule():
    """
    Get clinic schedule for a specific day.

    Query parameters:
        day: Day of week in Chinese (e.g., '星期一', '星期二')

    Response:
        {
            "day": "星期一",
            "morning": {"time": "08:00-12:00", "doctor": "王醫生", "capacity": 20},
            "afternoon": {"time": "14:00-18:00", "doctor": "李醫生", "capacity": 20},
            "evening": {"time": "19:00-21:00", "doctor": "王醫生", "capacity": 10}
        }
    """
    day = request.args.get('day', '星期一')

    if not day:
        return jsonify({
            "error": "Bad request",
            "message": "Missing parameter: day"
        }), 400

    try:
        engine = get_engine()
        schedule = engine.get_clinic_schedule(day)

        if "error" in schedule:
            return jsonify(schedule), 404

        return jsonify({
            "status": "success",
            "data": schedule
        })

    except Exception as e:
        logger.error(f"Schedule query error: {e}")
        return jsonify({
            "error": "Query failed",
            "message": str(e),
        }), 500


@bp.route('/clinic/staff', methods=['GET'])
def get_clinic_staff():
    """
    Get clinic staff roster.

    Optional parameters:
        position: Filter by position (e.g., '主治醫師', '護士')

    Response:
        {
            "status": "success",
            "count": 6,
            "data": [
                {
                    "id": "DOC001",
                    "name": "王醫生",
                    "position": "主治醫師",
                    "specialty": "內科",
                    "phone": "0912345678",
                    "email": "wang@clinic.tw"
                },
                ...
            ]
        }
    """
    position_filter = request.args.get('position')

    try:
        engine = get_engine()
        staff = engine.get_clinic_staff_roster()

        # Filter by position if specified
        if position_filter:
            staff = [s for s in staff if s.get('position') == position_filter]

        return jsonify({
            "status": "success",
            "count": len(staff),
            "data": staff
        })

    except Exception as e:
        logger.error(f"Staff query error: {e}")
        return jsonify({
            "error": "Query failed",
            "message": str(e),
        }), 500


@bp.route('/clinic/supplies', methods=['GET'])
def get_clinic_supplies():
    """
    Get clinic inventory/supplies status.

    Optional parameters:
        category: Filter by category (e.g., '藥物', '耗材')
        status: Filter by status ('LOW_STOCK' or 'OK')

    Response:
        {
            "status": "success",
            "count": 4,
            "low_stock_alert": 0,
            "data": [
                {
                    "name": "醫用手套",
                    "quantity": 500,
                    "min": 100,
                    "max": 1000,
                    "unit": "box",
                    "supplier": "台灣醫療用品公司",
                    "status": "✓ OK"
                },
                ...
            ]
        }
    """
    category_filter = request.args.get('category')
    status_filter = request.args.get('status')

    try:
        engine = get_engine()
        supplies = engine.get_clinic_supplies_status()

        # Filter by category if specified
        if category_filter:
            supplies = [s for s in supplies if s.get('category') == category_filter]

        # Filter by status if specified
        if status_filter:
            if status_filter.upper() == 'LOW_STOCK':
                supplies = [s for s in supplies if 'LOW STOCK' in s.get('status', '')]
            elif status_filter.upper() == 'OK':
                supplies = [s for s in supplies if 'OK' in s.get('status', '')]

        low_stock_count = sum(1 for s in supplies if 'LOW' in s.get('status', ''))

        return jsonify({
            "status": "success",
            "count": len(supplies),
            "low_stock_alert": low_stock_count,
            "data": supplies
        })

    except Exception as e:
        logger.error(f"Supplies query error: {e}")
        return jsonify({
            "error": "Query failed",
            "message": str(e),
        }), 500


# ============================================================================
# MEDICAL KNOWLEDGE (RAG Queries)
# ============================================================================

@bp.route('/medical/search', methods=['POST'])
def search_medical_knowledge():
    """
    Search medical knowledge using RAG (vector similarity).

    Request body:
        {
            "query": "What causes diabetes?",
            "top_k": 5  // Optional, default 5
        }

    Response:
        {
            "status": "success",
            "query": "What causes diabetes?",
            "count": 5,
            "results": [
                {
                    "title": "Article Title",
                    "content": "First 300 chars of content...",
                    "similarity": 0.87,
                    "source": "document.pdf"
                },
                ...
            ]
        }
    """
    data = request.get_json()

    if not data or 'query' not in data:
        return jsonify({
            "error": "Bad request",
            "message": "Missing required field: query"
        }), 400

    query = data['query']
    top_k = data.get('top_k', 5)

    try:
        engine = get_engine()
        results = engine.search_medical_knowledge(query, top_k=top_k)

        # Filter out errors
        valid_results = [r for r in results if "error" not in r]

        return jsonify({
            "status": "success",
            "query": query,
            "count": len(valid_results),
            "results": valid_results
        })

    except Exception as e:
        logger.error(f"Medical search error: {e}")
        return jsonify({
            "error": "Search failed",
            "message": str(e),
        }), 500


@bp.route('/medical/condition', methods=['POST'])
def search_medical_condition():
    """
    Search medical conditions in database.

    Request body:
        {
            "condition": "糖尿病"
        }

    Response:
        {
            "status": "success",
            "data": {
                "name": "糖尿病",
                "description": "...",
                "symptoms": ["多渴", "多尿", "疲勞"],
                "causes": ["胰島素分泌不足", "胰島素抵抗"],
                "risk_factors": ["肥胖", "家族史"],
                "treatments": ["飲食控制", "運動", "藥物治療"],
                "prevention": "...",
                "severity": {...},
                "icd_code": "E10-E14"
            }
        }
    """
    data = request.get_json()

    if not data or 'condition' not in data:
        return jsonify({
            "error": "Bad request",
            "message": "Missing required field: condition"
        }), 400

    condition = data['condition']

    try:
        engine = get_engine()
        result = engine.search_medical_conditions(condition)

        if "error" in result:
            return jsonify({
                "status": "not_found",
                "condition": condition
            }), 404

        return jsonify({
            "status": "success",
            "data": result
        })

    except Exception as e:
        logger.error(f"Condition search error: {e}")
        return jsonify({
            "error": "Search failed",
            "message": str(e),
        }), 500


# ============================================================================
# HYBRID QUERIES (Database + RAG Combined)
# ============================================================================

@bp.route('/diagnostic', methods=['POST'])
def diagnostic_query():
    """
    Hybrid diagnostic query: Symptom → Possible conditions.

    Combines:
    1. RAG search for medical knowledge articles
    2. Database search for exact condition matches

    Request body:
        {
            "symptoms": "多渴、多尿、疲勞"
        }

    Response:
        {
            "status": "success",
            "query": "多渴、多尿、疲勞",
            "rag_results": [
                {"title": "...", "content": "...", "similarity": 0.87}
            ],
            "db_results": [
                {"condition": "糖尿病", "description": "...", "symptoms": [...]}
            ],
            "recommendation": "Possible conditions: 糖尿病. Please consult a healthcare professional..."
        }
    """
    data = request.get_json()

    if not data or 'symptoms' not in data:
        return jsonify({
            "error": "Bad request",
            "message": "Missing required field: symptoms"
        }), 400

    symptoms = data['symptoms']

    try:
        engine = get_engine()
        result = engine.hybrid_diagnostic_query(symptoms)

        return jsonify({
            "status": "success",
            "query": result["query"],
            "rag_results": result["rag_results"],
            "db_results": result["db_results"],
            "recommendation": result["recommendation"]
        })

    except Exception as e:
        logger.error(f"Diagnostic query error: {e}")
        return jsonify({
            "error": "Query failed",
            "message": str(e),
        }), 500


@bp.route('/query', methods=['POST'])
def hybrid_intelligent_query():
    """
    Smart hybrid query with automatic intent detection and routing.

    Analyzes query to determine if it's:
    1. Clinic operational (schedule, staff, supplies) → Database
    2. Medical knowledge → RAG
    3. Combined clinic + medical → Hybrid

    Request body:
        {
            "query": "Can Dr. Wang treat my diabetes?"
        }

    Response:
        {
            "status": "success",
            "query": "Can Dr. Wang treat my diabetes?",
            "query_type": "hybrid",
            "clinic_info": { ... },
            "medical_info": { ... },
            "recommendation": "..."
        }
    """
    data = request.get_json()

    if not data or 'query' not in data:
        return jsonify({
            "error": "Bad request",
            "message": "Missing required field: query"
        }), 400

    query = data['query']

    try:
        engine = get_engine()
        result = engine.hybrid_clinic_medical_query(query)

        return jsonify({
            "status": "success",
            "query": result["query"],
            "query_type": result["query_type"],
            "clinic_info": result["clinic_info"],
            "medical_info": result["medical_info"]
        })

    except Exception as e:
        logger.error(f"Hybrid query error: {e}")
        return jsonify({
            "error": "Query failed",
            "message": str(e),
        }), 500


# ============================================================================
# HEALTH CHECK
# ============================================================================

@bp.route('/health', methods=['GET'])
def health_check():
    """
    Health check for hybrid query system.

    Response:
        {
            "status": "healthy",
            "medical_db": "available",
            "clinic_db": "available",
            "rag_engine": "available"
        }
    """
    try:
        engine = get_engine()

        return jsonify({
            "status": "healthy",
            "medical_db": "available",
            "clinic_db": "available",
            "rag_engine": "available" if engine.rag_available else "unavailable"
        })

    except Exception as e:
        return jsonify({
            "status": "unhealthy",
            "error": str(e)
        }), 503
