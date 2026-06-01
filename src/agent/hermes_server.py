"""
Hermes Agent Server - Task 11.3

Standalone server providing the Hermes Agent API on port 8642.
Enables unified intelligence as a decoupled service.
"""

import os
import sys
from flask import Flask, request, jsonify, Response, stream_with_context
import json
import logging

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../../')))

from src.agent.hermes_core import get_hermes_agent

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("hermes_server")

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    agent = get_hermes_agent()
    status = agent.get_context_status()
    return jsonify({
        "status": "ok",
        "service": "hermes-agent",
        "agent_status": status
    })

@app.route('/api/v1/chat', methods=['POST'])
def chat():
    """Blocking chat endpoint."""
    data = request.json
    query = data.get('query')
    history = data.get('history', [])
    image_data = data.get('image_data')

    if not query:
        return jsonify({"error": "Missing query"}), 400

    agent = get_hermes_agent()
    response, route, is_high_risk, confidence = agent.chat(query, history, image_data)
    
    return jsonify({
        "response": response,
        "route_used": route,
        "is_high_risk": is_high_risk,
        "confidence_score": confidence
    })

@app.route('/api/v1/chat/stream', methods=['POST'])
def chat_stream():
    """Streaming chat endpoint (SSE)."""
    data = request.json
    query = data.get('query')
    history = data.get('history', [])
    image_data = data.get('image_data')

    if not query:
        return jsonify({"error": "Missing query"}), 400

    agent = get_hermes_agent()

    def generate():
        for chunk in agent.chat_stream(query, history, image_data):
            yield chunk

    return Response(stream_with_context(generate()), mimetype='text/event-stream')

if __name__ == "__main__":
    port = int(os.environ.get("HERMES_PORT", 8642))
    logger.info(f"🚀 Hermes Agent Server starting on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
