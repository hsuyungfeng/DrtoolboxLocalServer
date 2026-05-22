from flask import Blueprint, request, jsonify, Response
from src.agent.hermes_core import get_hermes_agent
from src.services.logger_service import logger_service
import logging

logger = logging.getLogger(__name__)
chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/message', methods=['POST'])
def handle_message():
    agent = get_hermes_agent()
        
    data = request.json
    if not data or 'message' not in data:
        return jsonify({"error": "Missing 'message' field"}), 400
        
    user_id = data.get('user_id', 'anonymous')
    prompt = data['message']
    stream = data.get('stream', False)
    
    logger.info(f"Received message from {user_id}: {prompt} (stream: {stream})")
    
    if stream:
        return Response(agent.chat_stream(prompt), mimetype='text/event-stream')
    
    # Let Unified Hermes decide route and fetch response
    response, route_used = agent.chat(prompt)
    
    # Log the interaction for future model fine-tuning
    logger_service.log_interaction(
        user_id=user_id,
        prompt=prompt,
        response=response,
        route_used=route_used
    )
    
    return jsonify({
        "reply": response,
        "route_used": route_used
    })
