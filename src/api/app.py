"""
Flask API - Main application for DrtoolboxLocalServer.

Provides REST API for:
- Health checks (/health, /ready)
- LLM inference (/api/v1/generate, /api/v1/generate/stream)
- RAG operations (/api/v1/rag/*)
"""

import os
import logging
from flask import Flask, jsonify
from flask_cors import CORS
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

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
    app = Flask(__name__)
    
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
    from src.api.routes import inference, rag
    
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
            from src.llm.server import LlamaCppServer
            checks["llm"] = "available"
        except ImportError:
            checks["llm"] = "not_available"
        
        try:
            from src.rag.ingest import DocumentIngestor
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