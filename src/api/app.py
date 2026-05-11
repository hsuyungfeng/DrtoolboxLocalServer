"""
Flask API - Main application for DrtoolboxLocalServer.

Provides REST API for:
- Health checks (/health, /ready)
- LLM inference (/api/v1/generate, /api/v1/generate/stream)
- RAG operations (/api/v1/rag/*)
"""

import os
import sys
import logging

# Fix import paths
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from flask import Flask, jsonify
from flask_cors import CORS

# Load environment variables (optional - may not be available in all environments)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def create_app(config=None):
    """
    Create and configure Flask application.

    Args:
        config: Optional configuration dict

    Returns:
        Configured Flask application
    """
    # Set template folder to absolute path (src/templates)
    template_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'templates')
    app = Flask(__name__, template_folder=template_dir)
    
    # Load config
    app.config['JSON_SORT_KEYS'] = False
    app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True
    
    if config:
        app.config.update(config)
    
    # Enable CORS
    CORS(app, resources={
        r"/api/*": {
            "origins": "*",
            "methods": ["GET", "POST", "OPTIONS"],
            "allow_headers": ["Content-Type", "Authorization"],
        }
    })
    
    # Register routes
    _register_routes(app)
    
    # Error handlers
    _register_error_handlers(app)
    
    logger.info("Flask application created")
    
    return app


def _register_routes(app):
    """Register all API routes."""
    from api.routes import inference, rag, hybrid, clinic_his
    from api.routes.line_bot import line_bp
    from api.routes.staff_api import staff_bp
    from api.routes.patient_intake import patient_intake_bp
    from api.routes.patient_dashboard import patient_dashboard_bp
    from api.routes.staff_dashboard import staff_dashboard_bp

    # Health check routes
    @app.route('/health', methods=['GET'])
    def health_check():
        """Basic health check."""
        return jsonify({
            "status": "healthy",
            "service": "DrtoolboxLocalServer",
            "version": os.getenv("APP_VERSION", "1.0.0"),
        })
    
    @app.route('/ready', methods=['GET'])
    def readiness_check():
        """Readiness check - includes dependencies."""
        checks = {
            "status": "ready",
            "service": "DrtoolboxLocalServer",
        }
        
        # Check API dependencies
        try:
            from llm.server import LlamaCppServer
            checks["llm"] = "available"
        except ImportError:
            checks["llm"] = "not_available"

        try:
            from rag.ingest import DocumentIngestor
            checks["rag"] = "available"
        except ImportError:
            checks["rag"] = "not_available"
        
        # All dependencies must be available
        if checks.get("llm") == "not_available":
            checks["status"] = "degraded"
        
        return jsonify(checks)
    
    # Inference routes
    app.register_blueprint(inference.bp)

    # RAG routes
    app.register_blueprint(rag.bp)

    # Hybrid query routes (Database + RAG combined)
    app.register_blueprint(hybrid.bp)

    # HIS integration routes
    app.register_blueprint(clinic_his.bp)

    # LINE bot webhook routes
    app.register_blueprint(line_bp)

    # Staff API routes (conversation history, escalations)
    app.register_blueprint(staff_bp)

    # Patient Intake routes (form submission, idempotency)
    app.register_blueprint(patient_intake_bp)

    # Patient Dashboard routes (read-only view)
    app.register_blueprint(patient_dashboard_bp)

    # Staff Dashboard routes (CRUD operations)
    app.register_blueprint(staff_dashboard_bp)

    # Root route
    @app.route('/', methods=['GET'])
    def root():
        """API root information."""
        return jsonify({
            "service": "DrtoolboxLocalServer API",
            "version": "1.0.0",
            "endpoints": {
                "health": "/health",
                "ready": "/ready",
                "generate": "/api/v1/generate",
                "generate_stream": "/api/v1/generate/stream",
                "rag_query": "/api/v1/rag/query",
                "rag_search": "/api/v1/rag/search",
                "rag_ingest": "/api/v1/rag/ingest",
                "hybrid_query": "/api/v1/hybrid/query",
                "hybrid_diagnostic": "/api/v1/hybrid/diagnostic",
                "hybrid_clinic_schedule": "/api/v1/hybrid/clinic/schedule",
                "hybrid_clinic_staff": "/api/v1/hybrid/clinic/staff",
                "hybrid_clinic_supplies": "/api/v1/hybrid/clinic/supplies",
                "hybrid_medical_search": "/api/v1/hybrid/medical/search",
                "hybrid_medical_condition": "/api/v1/hybrid/medical/condition",
                "hybrid_health": "/api/v1/hybrid/health",
                "line_webhook": "/api/line/webhook",
                "line_health": "/api/line/health",
            }
        })


def _register_error_handlers(app):
    """Register error handlers."""
    
    @app.errorhandler(400)
    def bad_request(error):
        return jsonify({
            "error": "Bad request",
            "message": str(error),
        }), 400
    
    @app.errorhandler(404)
    def not_found(error):
        return jsonify({
            "error": "Not found",
            "message": "Resource not found",
        }), 404
    
    @app.errorhandler(500)
    def internal_error(error):
        logger.error(f"Internal error: {error}")
        return jsonify({
            "error": "Internal error",
            "message": "An internal error occurred",
        }), 500
    
    @app.errorhandler(503)
    def service_unavailable(error):
        return jsonify({
            "error": "Service unavailable",
            "message": str(error),
        }), 503


# Create app instance
app = create_app()


if __name__ == '__main__':
    port = int(os.getenv("PORT", 8080))
    debug = os.getenv("FLASK_DEBUG", "false").lower() == "true"
    
    app.run(
        host="0.0.0.0",
        port=port,
        debug=debug,
    )