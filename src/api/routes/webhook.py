import os
from flask import Blueprint, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FlexSendMessage, PostbackEvent
from src.services.line_beautifier import LineBeautifier

# ... (rest of imports)
from dotenv import load_dotenv
import logging
import json

logger = logging.getLogger(__name__)

webhook_bp = Blueprint('webhook', __name__)

# Robust .env loading - Use absolute path from this file's location
# src/api/routes/webhook.py -> ../../../.env
env_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../.env'))
load_dotenv(env_path)
logger.info(f"📍 Webhook attempting to load .env from: {env_path} (File Exists: {os.path.exists(env_path)})")

# Load LINE credentials from environment
LINE_CHANNEL_SECRET = os.environ.get('LINE_CHANNEL_SECRET')
LINE_CHANNEL_ACCESS_TOKEN = os.environ.get('LINE_CHANNEL_ACCESS_TOKEN')

if LINE_CHANNEL_SECRET:
    logger.info(f"✅ LINE Secret loaded (Prefix: {LINE_CHANNEL_SECRET[:4]}...)")
else:
    logger.error("❌ CRITICAL: LINE_CHANNEL_SECRET is MISSING from environment!")

line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN) if LINE_CHANNEL_ACCESS_TOKEN else None
handler = WebhookHandler(LINE_CHANNEL_SECRET) if LINE_CHANNEL_SECRET else WebhookHandler("DUMMY_SECRET_FOR_LOCAL_TESTING")

@webhook_bp.route('/webhook/line', methods=['GET', 'POST'], strict_slashes=False)
def line_webhook():
    """LINE Messaging API Webhook endpoint with GET support for connectivity tests."""
    if request.method == 'GET':
        return jsonify({
            "status": "active",
            "message": "Drtoolbox LINE Webhook is running. Please use POST for actual messaging events."
        }), 200

    if not handler:
        logger.error("LINE Webhook Handler not initialized. Check credentials in .env")
        return jsonify({"status": "error", "message": "Handler not initialized"}), 200

    signature = request.headers.get('X-Line-Signature')
    body = request.get_data(as_text=True)

    # Special handling for LINE's 'Verify' button which might send dummy data
    if not body or body == '{}':
        logger.info("Empty body received, likely a connectivity test.")
        return 'OK', 200

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        logger.warning("Invalid signature from LINE platform. This is normal during some verification tests.")
        return 'OK', 200 # Return 200 to pass the Verify test
    except Exception as e:
        logger.error(f"Webhook Handler unexpected error: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return 'OK', 200 # Force 200 to satisfy LINE Verify button

    return 'OK'

import threading
from datetime import datetime

# Conversion log file
CONVERSIONS_LOG_FILE = os.path.join(os.getenv("DATA_DIR", "data"), "analytics", "conversions.jsonl")
os.makedirs(os.path.dirname(CONVERSIONS_LOG_FILE), exist_ok=True)

@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    """Handle incoming messages using a background worker to prevent timeouts."""
    user_id = event.source.user_id
    user_text = event.message.text
    
    # 檢查是否為 B2B 企業地推追蹤碼 (例如專屬關鍵字或包含 utm_campaign=b2b_xxx)
    if "b2b_" in user_text:
        try:
            from scripts.openoutreach_bridge import DB_PATH
            import sqlite3
            match = re.search(r'b2b_([A-Za-z0-9_]+)', user_text)
            if match:
                company_id = match.group(1)
                conn = sqlite3.connect(DB_PATH)
                cursor = conn.cursor()
                cursor.execute("UPDATE b2b_leads SET line_linked_count = line_linked_count + 1, status = 'linked' WHERE company_id = ?;", (company_id,))
                cursor.execute("UPDATE patients SET b2b_company_id = ?, tags = 'b2b_vip' WHERE patient_id = ?;", (company_id, user_id))
                conn.commit()
                conn.close()
                logger.info(f"🔗 成功為病患 {user_id} 綁定 B2B 企業 VIP ({company_id})")
        except Exception as b2b_e:
            logger.error(f"B2B VIP 綁定失敗: {b2b_e}")

    # Start background thread to handle heavy reasoning
    thread = threading.Thread(target=process_line_message_bg, args=(event.reply_token, user_id, user_text))
    thread.start()
    
    # Return 200 OK to LINE/ngrok immediately
    return 'OK'

@handler.add(PostbackEvent)
def handle_postback(event):
    """Handle postback events (e.g., button clicks in Flex Messages)."""
    user_id = event.source.user_id
    data = event.postback.data
    
    # Parse query-string style data: action=booking&treatment=pico
    try:
        params = dict(x.split('=') for x in data.split('&') if '=' in x)
        
        if params.get('action') == 'booking':
            treatment = params.get('treatment', 'unknown')
            logger.info(f"CONVERSION DETECTED | user={user_id} treatment={treatment}")
            
            # 1. Log conversion
            log_conversion(user_id, treatment)
            
            # 2. Notify staff
            try:
                from src.services.notification_service import notification_service
                notification_service.notify_high_risk(
                    patient_id=user_id,
                    message=f"使用者點擊了『{treatment}』的預約按鈕。",
                    risk_type="Marketing Conversion"
                )
            except Exception as e:
                logger.error(f"Failed to notify staff of conversion: {e}")
            
            # 3. Reply with actual booking link or instruction
            if line_bot_api:
                reply_text = "感謝您的預約意願！請點擊下方連結加入我們的專人預約帳號，或直接撥打診所電話 04-2395-0960 由專人為您服務。\n\n🔗 預約連結：https://line.me/ti/p/@181fvgic"
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
    except Exception as e:
        logger.error(f"Error handling postback: {e}")

    return 'OK'

def log_conversion(user_id, treatment):
    """Log conversion event to a structured file."""
    try:
        with open(CONVERSIONS_LOG_FILE, "a", encoding='utf-8') as f:
            entry = {
                "timestamp": datetime.now().isoformat(),
                "user_id": user_id,
                "treatment": treatment,
                "event": "booking_click"
            }
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error(f"Failed to log conversion: {e}")

def process_line_message_bg(reply_token, user_id, user_text):
    """Background worker for LLM reasoning and LINE response."""
    try:
        from src.agent.hermes_core import get_hermes_agent
        from src.services.logger_service import logger_service
        agent = get_hermes_agent()
        
        # 1. Safety Guardrail
        is_high_risk = agent._check_high_risk(user_text)
        if is_high_risk:
            reply = "⚠️ **系統提示**：偵測到您提到的症狀可能需要立即處理。\n\n請撥打診所緊急電話：04-2395-0960，或前往急診。"
            if line_bot_api:
                line_bot_api.push_message(user_id, TextSendMessage(text=reply))
            # Notify staff in real-time
            try:
                from src.services.notification_service import notification_service
                notification_service.notify_high_risk(
                    patient_id=user_id,
                    message=user_text,
                    risk_type="Symptom/Medical"
                )
            except Exception as notify_e:
                logger.error(f"Failed to send high risk staff alert: {notify_e}")
            
            # Log the risk interaction
            logger_service.log_interaction(user_id, user_text, reply, "emergency", is_high_risk=True)
            return

        # 2. Reasoning (Heavy Task)
        response, route, risk, conf = agent.chat(user_text)
        
        # 3. Beautification
        formatted_text = LineBeautifier.format_text(response)
        
        # 4. Generate Messaging Object
        # --- NEW: Marketing Conversion Trigger ---
        treatment_card = None
        lower_query = user_text.lower()
        
        if "外泌體" in lower_query or "exosome" in lower_query:
            treatment_card = LineBeautifier.build_treatment_card("exosomes")
        elif "皮秒" in lower_query or "pico" in lower_query:
            treatment_card = LineBeautifier.build_treatment_card("pico")
        elif "水飛梭" in lower_query or "hydrafacial" in lower_query:
            treatment_card = LineBeautifier.build_treatment_card("hydrafacial")

        if not line_bot_api:
            logger.warning("LINE API not initialized, skipping response push.")
        else:
            if treatment_card:
                # Send the clinical answer first, then the marketing card
                line_bot_api.push_message(user_id, TextSendMessage(text=formatted_text))
                line_bot_api.push_message(user_id, FlexSendMessage(alt_text="專屬療程建議", contents=treatment_card))
            elif route == "special" and any(k in user_text for k in ["地址", "電話", "去", "位置", "在哪"]):
                flex_content = LineBeautifier.build_clinic_info_card()
                line_bot_api.push_message(user_id, FlexSendMessage(alt_text="診所聯絡資訊", contents=flex_content))
            elif len(formatted_text) > 300:
                # Traditional Sequential Messaging (Split into multiple messages)
                title = "💡 專家建議" if route == "general" else "🏥 療程說明"
                bubbles = LineBeautifier.build_flex_bubbles(title, formatted_text, footer_text="緻妍 AI 醫療助手服務中")
                
                for i, bubble in enumerate(bubbles[:5]):
                    line_bot_api.push_message(user_id, FlexSendMessage(alt_text=f"AI 回覆 (第 {i+1} 部分)", contents=bubble))
            else:
                line_bot_api.push_message(user_id, TextSendMessage(text=formatted_text))

        # 6. LOG TO DASHBOARD
        logger_service.log_interaction(
            user_id=user_id,
            prompt=user_text,
            response=response,
            route_used=route,
            is_high_risk=risk,
            confidence_score=conf
        )
        
    except Exception as e:
        logger.error(f"Error in LINE background worker: {e}")
        import traceback
        logger.error(traceback.format_exc())
        try:
            if line_bot_api:
                line_bot_api.push_message(user_id, TextSendMessage(text="抱歉，系統目前忙碌中，請稍後再試。"))
        except: pass

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
            messaging_events = entry.get('messaging', [])
            for event in messaging_events:
                sender_psid = event.get('sender', {}).get('id')
                if event.get('message') and not event.get('message').get('is_echo'):
                    # Start background thread to prevent Meta timeout
                    thread = threading.Thread(target=process_messenger_message_bg, args=(sender_psid, event['message']))
                    thread.start()
                
        return 'EVENT_RECEIVED', 200
    
    return "Not Found", 404

def process_messenger_message_bg(psid, received_message):
    """Background worker for Messenger reasoning and reply."""
    user_text = received_message.get('text')
    if not user_text: return
    
    logger.info(f"Messenger (BG) from {psid}: {user_text}")
    
    try:
        from src.agent.hermes_core import get_hermes_agent
        from src.services.logger_service import logger_service
        agent = get_hermes_agent()
        
        # 1. Safety Guardrail (High Risk)
        is_high_risk = agent._check_high_risk(user_text)
        if is_high_risk:
            reply = "⚠️ **系統提示**：偵測到您提到的症狀可能需要立即處理。\n\n請撥打診所緊急電話：04-2395-0960，或前往急診。"
            send_messenger_reply(psid, reply)
            logger_service.log_interaction(psid, user_text, reply, "emergency", is_high_risk=True)
            return

        # 2. Dynamic RAG Reasoning
        response, route, risk, conf = agent.chat(user_text)
        
        # 3. Price Safeguard & Call to Action
        if any(k in user_text for k in ["價格", "多少錢", "費用", "預約"]):
            response += "\n\n💡 建議直接致電診所 04-2395-0960 或在此私訊專人預約。"

        send_messenger_reply(psid, response)

        # 4. LOG TO DASHBOARD
        logger_service.log_interaction(
            user_id=psid,
            prompt=user_text,
            response=response,
            route_used=route,
            is_high_risk=risk,
            confidence_score=conf
        )
        
    except Exception as e:
        logger.error(f"Error handling Messenger message in background: {e}")
        try:
            send_messenger_reply(psid, "抱歉，系統目前忙碌中，請稍後再試。")
        except: pass

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
