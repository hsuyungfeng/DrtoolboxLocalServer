"""
Mitmproxy script to intercept doctor-toolbox.com HTTP/WebSocket requests and responses.

Intercepts:
1. Audio files (.mp3, .wav, .webm, audio/*)
2. SOAP, Transcription, and Consultation JSON responses from cloud
3. Auto-saves files to ./data/intercepted_audios/ and calls local comparison API
"""

import os
import json
import time
import logging
from mitmproxy import http

logger = logging.getLogger("mitm_interceptor")
logging.basicConfig(level=logging.INFO)

TARGET_DOMAIN = "doctor-toolbox.com"
OUTPUT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../data/intercepted_audios"))
os.makedirs(OUTPUT_DIR, exist_ok=True)


def response(flow: http.HTTPFlow) -> None:
    """Intercept responses matching doctor-toolbox.com"""
    request_host = flow.request.pretty_host
    if TARGET_DOMAIN not in request_host:
        return

    url = flow.request.url
    method = flow.request.method
    status_code = flow.response.status_code
    content_type = flow.response.headers.get("content-type", "")

    timestamp = time.strftime("%Y%m%d_%H%M%S")
    logger.info(f"[INTERCEPT] {method} {url} -> {status_code} ({content_type})")

    # 1. Intercept Audio Data
    if "audio" in content_type or any(url.endswith(ext) for ext in [".wav", ".mp3", ".webm", ".ogg"]):
        audio_filename = f"audio_{timestamp}.wav"
        save_path = os.path.join(OUTPUT_DIR, audio_filename)
        with open(save_path, "wb") as f:
            f.write(flow.response.content)
        logger.info(f"✅ Saved intercepted audio to: {save_path}")

    # 2. Intercept JSON / SOAP / Transcript Responses
    if "application/json" in content_type or "text/" in content_type:
        try:
            res_text = flow.response.get_text()
            if not res_text or not res_text.strip():
                return
            
            # Check if text contains SOAP or transcription keywords
            if any(k in res_text.lower() for k in ["subjective", "objective", "assessment", "plan", "transcript", "soap", "病歷"]):
                json_filename = f"intercept_{timestamp}.json"
                json_path = os.path.join(OUTPUT_DIR, json_filename)
                
                record = {
                    "url": url,
                    "method": method,
                    "status_code": status_code,
                    "timestamp": timestamp,
                    "response_body": res_text
                }
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(record, f, ensure_ascii=False, indent=2)
                logger.info(f"✅ Saved intercepted SOAP/Transcript JSON to: {json_path}")
                
                # Auto-notify local server via HTTP POST
                _forward_to_local_server(record)
        except Exception as e:
            logger.error(f"Failed to process response body: {e}")


def _forward_to_local_server(record: dict):
    """Forward intercepted transcript & cloud SOAP to local DrtoolboxLocalServer for A/B comparison"""
    try:
        import requests
        local_api_url = "http://127.0.0.1:5000/api/dashboard/soap/intercept"
        requests.post(local_api_url, json=record, timeout=3)
        logger.info("⚡ Forwarded intercepted data to local comparison API.")
    except Exception as e:
        logger.warning(f"Could not forward to local server: {e}")
