import os
from flask import Blueprint, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import logging
import json

logger = logging.getLogger(__name__)

webhook_bp = Blueprint('webhook', __name__)

# Load LINE credentials from environment
LINE_CHANNEL_SECRET = os.getenv('LINE_CHANNEL_SECRET')
LINE_CHANNEL_ACCESS_TOKEN = os.getenv('LINE_CHANNEL_ACCESS_TOKEN')

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN) if LINE_CHANNEL_ACCESS_TOKEN else None
handler = WebhookHandler(LINE_CHANNEL_SECRET) if LINE_CHANNEL_SECRET else None

@webhook_bp.route('/webhook/line', methods=['GET', 'POST'], strict_slashes=False)
def line_webhook():
    """LINE Messaging API Webhook endpoint with GET support for connectivity tests."""
    if request.method == 'GET':
        return jsonify({
            "status": "active",
            "message": "Drtoolbox LINE Webhook is running. Please use POST for actual messaging events."
        }), 200

    if not handler:
        logger.error("LINE Webhook Handler not initialized. Check credentials.")
        return "Not Configured", 500

    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.warning("Invalid signature from LINE platform.")
        abort(400)
    except Exception as e:
        logger.error(f"Webhook Handler error: {e}")
        return "Error", 500

    return 'OK'

# Wrap message handling logic to be safe during initialization
if handler:
    @handler.add(MessageEvent, message=TextMessage)
    def handle_message(event):
        """Handle incoming text messages from LINE."""
        user_id = event.source.user_id
        user_text = event.message.text
        
        logger.info(f"LINE Message from {user_id}: {user_text}")
        
        try:
            # Import the unified agent
            from src.agent.hermes_core import get_hermes_agent
            agent = get_hermes_agent()
            
            # 1. Check for high-risk / Safety First
            is_high_risk = agent._check_high_risk(user_text)
            if is_high_risk:
                reply = "⚠️ **系統提示**：偵測到您提到的症狀可能需要立即處理。\n\n請撥打診所緊急電話：04-2395-0960，或直接前往最近的急診室。您的安全是我們的首要考量。"
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply))
                return

            # 2. Get AI Answer via RAG (Dynamic Knowledge Fallback)
            response, route, risk, conf = agent.chat(user_text)
            
            # 3. Handle Price Safeguard
            if any(k in user_text for k in ["價格", "多少錢", "費用", "預約"]):
                response += "\n\n💡 溫馨提醒：為了提供最準確的療程方案與專屬優惠，建議您直接致電診所或點擊下方選單進行預約面診。"

            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=response)
            )
            
        except Exception as e:
            logger.error(f"Error handling LINE message: {e}")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="抱歉，系統目前忙碌中，請稍後再試或直接致電診所。")
            )

# Load Messenger credentials
MESSENGER_PAGE_ACCESS_TOKEN = os.getenv('MESSENGER_PAGE_ACCESS_TOKEN')
MESSENGER_VERIFY_TOKEN = os.getenv('MESSENGER_VERIFY_TOKEN')
MESSENGER_APP_SECRET = os.getenv('MESSENGER_APP_SECRET')

@webhook_bp.route('/webhook/messenger', methods=['GET', 'POST'], strict_slashes=False)
def messenger_webhook():
    """Messenger Webhook for Meta Graph API."""
    if request.method == 'GET':
        # Verification logic for Meta app dashboard
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')
        
        if mode == 'subscribe' and token == MESSENGER_VERIFY_TOKEN:
            logger.info("Messenger Webhook Verified!")
            return challenge
        return "Forbidden", 403
    
    # POST - Handle incoming messages
    body = request.get_json()
    if body.get('object') == 'page':
        for entry in body.get('entry', []):
            webhook_event = entry.get('messaging', [])[0]
            sender_psid = webhook_event.get('sender', {}).get('id')
            
            if webhook_event.get('message') and not webhook_event.get('message').get('is_echo'):
                handle_messenger_message(sender_psid, webhook_event['message'])
                
        return 'EVENT_RECEIVED', 200
    
    return "Not Found", 404

def handle_messenger_message(psid, received_message):
    """Messenger specific message processing."""
    user_text = received_message.get('text')
    if not user_text: return # Skip media for now
    
    logger.info(f"Messenger Message from {psid}: {user_text}")
    
    try:
        import requests
        from src.agent.hermes_core import get_hermes_agent
        agent = get_hermes_agent()
        
        # 1. Safety Guardrail (High Risk)
        is_high_risk = agent._check_high_risk(user_text)
        if is_high_risk:
            reply = "⚠️ **系統提示**：偵測到您提到的症狀可能需要立即處理。\n\n請撥打診所緊急電話：04-2395-0960，或前往急診。"
            send_messenger_reply(psid, reply)
            return

        # 2. Dynamic RAG Reasoning
        response, route, risk, conf = agent.chat(user_text)
        
        # 3. Price Safeguard
        if any(k in user_text for k in ["價格", "多少錢", "費用", "預約"]):
            response += "\n\n💡 建議直接致電診所或於粉專私訊專人預約。"

        send_messenger_reply(psid, response)
        
    except Exception as e:
        logger.error(f"Error handling Messenger message: {e}")
        send_messenger_reply(psid, "抱歉，系統目前忙碌中，請稍後再試。")

def send_messenger_reply(psid, text):
    """Calls Meta Send API to reply to user."""
    if not MESSENGER_PAGE_ACCESS_TOKEN:
        logger.warning("Messenger Page Access Token not configured.")
        return

    url = f"https://graph.facebook.com/v19.0/me/messages?access_token={MESSENGER_PAGE_ACCESS_TOKEN}"
    payload = {
        "recipient": {"id": psid},
        "message": {"text": text},
        "messaging_type": "RESPONSE"
    }
    try:
        res = requests.post(url, json=payload, timeout=10)
        res.raise_for_status()
    except Exception as e:
        logger.error(f"Messenger Send API error: {e}")
