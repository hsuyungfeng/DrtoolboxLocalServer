"""
LINE Bot Webhook Endpoint — Task 5

POST /api/line/webhook receives LINE Messaging API events,
validates HMAC-SHA256 signatures, parses message types, and
dispatches to message_router for processing.

LINE expects 200 OK within 3 seconds; heavy processing is
handed off asynchronously via a background thread.
"""

import hashlib
import hmac
import base64
import logging
import os
import threading
import time
from flask import Blueprint, request, jsonify

logger = logging.getLogger(__name__)

line_bp = Blueprint("line", __name__, url_prefix="/api/line")

# ────────────────────────────────────────────────────────────
# Signature validation
# ────────────────────────────────────────────────────────────

def _verify_signature(channel_secret: str, body: bytes, signature: str) -> bool:
    """Validate LINE webhook signature (HMAC-SHA256)."""
    try:
        hash_digest = hmac.new(
            channel_secret.encode("utf-8"),
            body,
            hashlib.sha256,
        ).digest()
        expected = base64.b64encode(hash_digest).decode("utf-8")
        return hmac.compare_digest(expected, signature)
    except Exception as exc:
        logger.warning("Signature verification error: %s", exc)
        return False


# ────────────────────────────────────────────────────────────
# Message parsing helpers
# ────────────────────────────────────────────────────────────

def _parse_event(event: dict) -> dict | None:
    """
    Parse a single LINE event dict into a normalised message envelope.

    Returns None for non-message events (follow, unfollow, postback …).
    """
    event_type = event.get("type")
    if event_type != "message":
        logger.debug("Skipping non-message event type: %s", event_type)
        return None

    source = event.get("source", {})
    user_id = source.get("userId", "unknown")
    reply_token = event.get("replyToken", "")
    message = event.get("message", {})
    msg_type = message.get("type", "unknown")

    envelope = {
        "user_id": user_id,
        "reply_token": reply_token,
        "message_type": msg_type,
        "raw_message": message,
        "received_at": time.time(),
    }

    if msg_type == "text":
        envelope["text"] = message.get("text", "")
    elif msg_type == "image":
        envelope["text"] = "[IMAGE]"
        envelope["image_id"] = message.get("id", "")
    elif msg_type == "location":
        envelope["text"] = (
            f"[LOCATION] {message.get('title', '')} "
            f"lat={message.get('latitude')} lng={message.get('longitude')}"
        )
    else:
        # sticker, video, audio, file — treat as non-text
        envelope["text"] = f"[{msg_type.upper()}]"

    logger.info(
        "Parsed LINE message | user=%s type=%s",
        user_id,
        msg_type,
    )
    return envelope


# ────────────────────────────────────────────────────────────
# Background dispatcher
# ────────────────────────────────────────────────────────────

def _dispatch_background(envelopes: list[dict]) -> None:
    """Process message envelopes in a background thread."""
    from services.message_router import route_message  # lazy import to avoid circular

    for env in envelopes:
        try:
            route_message(env)
        except Exception as exc:
            logger.error(
                "Background dispatch error | user=%s error=%s",
                env.get("user_id"),
                exc,
                exc_info=True,
            )


# ────────────────────────────────────────────────────────────
# Webhook endpoint
# ────────────────────────────────────────────────────────────

@line_bp.route("/webhook", methods=["POST"])
def webhook():
    """
    Receive LINE Messaging API events.

    LINE requires an HTTP 200 response within 3 seconds.
    Signature validation happens synchronously; message
    processing is deferred to a background thread.
    """
    channel_secret = os.getenv("LINE_CHANNEL_SECRET", "")
    signature = request.headers.get("X-Line-Signature", "")
    body_bytes = request.get_data()

    # ── Signature validation (skip in test/dev if secret not set) ──
    if channel_secret:
        if not signature:
            logger.warning("Webhook request missing X-Line-Signature header")
            return jsonify({"error": "Missing signature"}), 400
        if not _verify_signature(channel_secret, body_bytes, signature):
            logger.warning("Webhook signature validation failed")
            return jsonify({"error": "Invalid signature"}), 400

    # ── Parse JSON body ──
    data = request.get_json(silent=True) or {}
    events = data.get("events", [])

    if not events:
        # Verification request from LINE developer console — always 200
        return "", 200

    # ── Parse events into envelopes ──
    envelopes = []
    for event in events:
        env = _parse_event(event)
        if env is not None:
            envelopes.append(env)
            logger.info(
                "Audit | received LINE event | user=%s type=%s",
                env["user_id"],
                env["message_type"],
            )

    # ── Dispatch processing in background (returns 200 immediately) ──
    if envelopes:
        t = threading.Thread(
            target=_dispatch_background,
            args=(envelopes,),
            daemon=True,
        )
        t.start()

    return "", 200


# ────────────────────────────────────────────────────────────
# Health probe
# ────────────────────────────────────────────────────────────

@line_bp.route("/health", methods=["GET"])
def health():
    """LINE bot subsystem health check."""
    channel_secret_set = bool(os.getenv("LINE_CHANNEL_SECRET"))
    channel_token_set = bool(os.getenv("LINE_CHANNEL_ACCESS_TOKEN"))
    return jsonify({
        "status": "ok",
        "line_channel_secret_configured": channel_secret_set,
        "line_channel_token_configured": channel_token_set,
    })
