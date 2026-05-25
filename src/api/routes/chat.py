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
    image_data = data.get('image') # Base64 image data
    
    logger.info(f"Received message from {user_id}: {prompt} (stream: {stream}, has_image: {image_data is not None})")
    
    if stream:
        return Response(agent.chat_stream(prompt, image_data=image_data), mimetype='text/event-stream')
    
    # Let Unified Hermes decide route and fetch response
    response, route_used, is_high_risk = agent.chat(prompt, image_data=image_data)
    
    # Log the interaction for future model fine-tuning
    logger_service.log_interaction(
        user_id=user_id,
        prompt=prompt,
        response=response,
        route_used=route_used,
        is_high_risk=is_high_risk
    )
    
    return jsonify({
        "reply": response,
        "route_used": route_used,
        "is_high_risk": is_high_risk
    })
