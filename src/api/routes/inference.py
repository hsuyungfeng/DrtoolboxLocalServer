"""
Inference API routes for LLM generation.

Endpoints:
- POST /api/v1/generate - Synchronous text generation
- POST /api/v1/generate/stream - Streaming text generation
"""

import logging
from flask import Blueprint, request, jsonify, Response, stream_with_context
from typing import Optional

from src.llm.server import LlamaCppServer, GenerationConfig

logger = logging.getLogger(__name__)

bp = Blueprint('inference', __name__, url_prefix='/api/v1')

# Global server instance (initialized lazily)
_server: Optional[LlamaCppServer] = None


def get_server() -> LlamaCppServer:
    """Get or create server instance."""
    global _server
    
    if _server is None:
        model_path = "models/Qwen3-6B-Q8_0.gguf"
        config_path = "config/llama_config.json"
        
        _server = LlamaCppServer(
            model_path=model_path,
            config_path=config_path,
        )
        
        # Note: Call load_model() separately to avoid blocking API start
        # In production, use gunicorn with proper model pre-loading
    
    return _server


@bp.route('/generate', methods=['POST'])
def generate():
    """
    Synchronous text generation.
    
    Request body:
        {
            "prompt": "Input text prompt",
            "max_tokens": 1024,          // Optional, default 1024
            "temperature": 0.7,           // Optional, default 0.7
            "top_p": 0.9,              // Optional, default 0.9
            "stop": ["</s>"]            // Optional
        }
    
    Response:
        {
            "text": "Generated text",
            "model": "Qwen3-6B-Q8_0",
            "prompt_tokens": 50,
            "completion_tokens": 200,
            "total_tokens": 250,
            "latency_ms": 250.0,
            "finish_reason": "stop"
        }
    """
    data = request.get_json()
    
    if not data or 'prompt' not in data:
        return jsonify({
            "error": "Bad request",
            "message": "Missing required field: prompt"
        }), 400
    
    prompt = data['prompt']
    
    # Build config
    config = GenerationConfig(
        max_tokens=data.get('max_tokens', 1024),
        temperature=data.get('temperature', 0.7),
        top_p=data.get('top_p', 0.9),
        top_k=data.get('top_k', 40),
        repeat_penalty=data.get('repeat_penalty', 1.1),
        stop=data.get('stop', ["</s>", "USER:"]),
    )
    
    try:
        server = get_server()
        
        if not server.is_ready():
            # Check if model is loaded
            if server.model is None:
                return jsonify({
                    "error": "Service unavailable",
                    "message": "Model not loaded. Call /load first or use gunicorn."
                }), 503
        
        result = server.generate(prompt, config)
        
        return jsonify({
            "text": result.text,
            "model": result.model,
            "prompt_tokens": result.prompt_tokens,
            "completion_tokens": result.completion_tokens,
            "total_tokens": result.total_tokens,
            "latency_ms": result.latency_ms,
            "finish_reason": result.finish_reason,
        })
        
    except RuntimeError as e:
        logger.error(f"Generation error: {e}")
        return jsonify({
            "error": "Generation failed",
            "message": str(e),
        }), 503
    
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({
            "error": "Internal error",
            "message": str(e),
        }), 500


@bp.route('/generate/stream', methods=['POST'])
def generate_stream():
    """
    Streaming text generation (token-by-token).
    
    Request body:
        Same as /generate
    
    Response:
        Server-sent events with tokens:
        
        data: {"token": "generated", "done": false}
        ...
        data: {"token": "", "done": true}
    """
    data = request.get_json()
    
    if not data or 'prompt' not in data:
        return jsonify({
            "error": "Bad request",
            "message": "Missing required field: prompt"
        }), 400
    
    prompt = data['prompt']
    
    config = GenerationConfig(
        max_tokens=data.get('max_tokens', 1024),
        temperature=data.get('temperature', 0.7),
        top_p=data.get('top_p', 0.9),
        top_k=data.get('top_k', 40),
        repeat_penalty=data.get('repeat_penalty', 1.1),
        stop=data.get('stop', ["</s>", "USER:"]),
    )
    
    try:
        server = get_server()
        
        if not server.is_ready():
            if server.model is None:
                return jsonify({
                    "error": "Service unavailable",
                    "message": "Model not loaded"
                }), 503
        
        def generate():
            try:
                for token in server.streaming_generate(prompt, config):
                    yield f"data: {{'token': {repr(token)}, 'done': false}}\n\n"
                
                yield f"data: {{'token': '', 'done': true}}\n\n"
                
            except Exception as e:
                yield f"data: {{'error': {repr(str(e))}}}\n\n"
        
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no',
            }
        )
        
    except Exception as e:
        logger.error(f"Stream error: {e}")
        return jsonify({
            "error": "Stream failed",
            "message": str(e),
        }), 500


@bp.route('/load', methods=['POST'])
def load_model():
    """
    Load LLM model.
    
    Request body:
        {
            "model_path": "models/Qwen3-6B-Q8_0.gguf"  // Optional
        }
    
    Response:
        {
            "status": "loaded",
            "model": "Qwen3-6B-Q8_0",
            "latency_ms": 5000.0
        }
    """
    import time
    
    body = request.get_json() or {}
    model_path = body.get('model_path', 'models/Qwen3-6B-Q8_0.gguf')
    
    try:
        server = get_server()
        server.model_path = model_path
        
        start = time.time()
        success = server.load_model()
        latency_ms = (time.time() - start) * 1000
        
        if success:
            return jsonify({
                "status": "loaded",
                "model": server.model_path,
                "latency_ms": latency_ms,
            })
        else:
            return jsonify({
                "error": "Load failed",
                "message": "Model loading returned false"
            }), 500
            
    except Exception as e:
        logger.error(f"Load error: {e}")
        return jsonify({
            "error": "Load failed",
            "message": str(e),
        }), 500


@bp.route('/status', methods=['GET'])
def get_status():
    """Get server status and GPU memory info."""
    try:
        server = get_server()
        
        info = {
            "ready": server.is_ready(),
            "model_loaded": server.model is not None,
            "model_path": server.model_path,
            "batch_size": server.get_batch_size(),
            "queue_depth": server.get_queue_depth(),
        }
        
        # Add GPU info if available
        gpu_info = server.get_gpu_memory_info()
        if gpu_info.get("available"):
            info["gpu_memory"] = gpu_info
        
        return jsonify(info)
        
    except Exception as e:
        return jsonify({
            "error": "Status check failed",
            "message": str(e),
        }), 500


@bp.route('/unload', methods=['POST'])
def unload_model():
    """Unload model from memory."""
    try:
        global _server
        
        if _server:
            _server.shutdown()
            _server = None
        
        return jsonify({"status": "unloaded"})
        
    except Exception as e:
        return jsonify({
            "error": "Unload failed",
            "message": str(e),
        }), 500