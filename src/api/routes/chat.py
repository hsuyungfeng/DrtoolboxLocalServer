from flask import Blueprint, request, jsonify
from src.agent.hermes_router import HermesRouter
from src.services.logger_service import logger_service
import logging

logger = logging.getLogger(__name__)
chat_bp = Blueprint('chat', __name__)

router = None

@chat_bp.route('/message', methods=['POST'])
def handle_message():
    global router
    if router is None:
        router = HermesRouter()
        
    data = request.json
    if not data or 'message' not in data:
        return jsonify({"error": "Missing 'message' field"}), 400
        
    user_id = data.get('user_id', 'anonymous')
    prompt = data['message']
    
    logger.info(f"Received message from {user_id}: {prompt}")
    
    # Let Hermes decide route and fetch response
    response, route_used = router.chat(prompt)
    
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
