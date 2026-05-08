"""
Message Router — Task 6

Classifies incoming LINE message envelopes and routes them to the
appropriate handler:

  confidence >= 60%  →  line_responder.send_rag_response()
  confidence <  60%  →  escalation flag (Wave 3 Task 11)

Decision D-03: default route is RAG (all messages go to RAG first).
Decision D-04: escalation threshold is < 60% confidence.

Logging: every routing decision is logged with user_id, intent,
confidence, and final routing_decision.
"""

import logging
import os
import re
import time

import requests

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────
RAG_API_URL = os.getenv("RAG_API_URL", "http://127.0.0.1:8080/api/v1/rag/query")
ESCALATION_THRESHOLD = float(os.getenv("ESCALATION_THRESHOLD", "0.60"))
RAG_REQUEST_TIMEOUT = float(os.getenv("RAG_REQUEST_TIMEOUT", "4.0"))  # keep total < 5s

# Simple abuse / malformed detection patterns
_ABUSE_PATTERNS = re.compile(
    r"(fuck|shit|bitch|damn|asshole|idiot|stupid|hate you)",
    re.IGNORECASE,
)


# ── Intent classification ──────────────────────────────────────────

def _classify_intent(text: str) -> str:
    """
    Lightweight rule-based intent classification.

    Returns one of: 'medical_query' | 'appointment' | 'medication' |
                    'abusive' | 'greeting' | 'general'
    """
    if _ABUSE_PATTERNS.search(text):
        return "abusive"

    t = text.lower()

    if any(kw in t for kw in ["藥", "medication", "drug", "pill", "dose", "藥物"]):
        return "medication"
    if any(kw in t for kw in ["掛號", "appointment", "schedule", "clinic", "預約"]):
        return "appointment"
    if any(kw in t for kw in ["hi", "hello", "你好", "哈囉", "嗨"]):
        return "greeting"
    if any(kw in t for kw in [
        "symptom", "pain", "fever", "cough", "disease", "treatment",
        "症狀", "疼痛", "發燒", "咳嗽", "疾病", "治療",
    ]):
        return "medical_query"

    return "general"


# ── RAG query ─────────────────────────────────────────────────────

def _query_rag(text: str, n_results: int = 5) -> dict:
    """
    Call the RAG API endpoint.

    Returns dict with at minimum: {answer, confidence}
    Raises on network / timeout errors.
    """
    payload = {"prompt": text, "n_results": n_results}
    response = requests.post(
        RAG_API_URL,
        json=payload,
        timeout=RAG_REQUEST_TIMEOUT,
    )
    response.raise_for_status()
    return response.json()


# ── Main routing entry point ───────────────────────────────────────

def route_message(envelope: dict) -> dict:
    """
    Route a parsed LINE message envelope.

    Args:
        envelope: normalised message dict from line_bot.py
            {user_id, reply_token, message_type, text, received_at, …}

    Returns:
        routing result dict:
        {
            "user_id": str,
            "routing_decision": "rag_response" | "escalation",
            "intent": str,
            "confidence": float | None,
            "rag_result": dict | None,
            "error": str | None,
        }
    """
    user_id = envelope.get("user_id", "unknown")
    text = envelope.get("text", "")
    reply_token = envelope.get("reply_token", "")
    start_ts = time.time()

    # ── Step 1: classify intent ──
    intent = _classify_intent(text)

    # ── Step 2: auto-escalate abusive / malformed messages ──
    if intent == "abusive" or not text.strip():
        logger.info(
            "Routing | user=%s intent=%s confidence=N/A decision=escalation (auto)",
            user_id, intent,
        )
        return _build_result(
            user_id=user_id,
            routing_decision="escalation",
            intent=intent,
            confidence=None,
            rag_result=None,
            error=None,
        )

    # ── Step 3: query RAG (D-03: default route) ──
    rag_result = None
    confidence = None
    error = None

    try:
        rag_result = _query_rag(text)
        confidence = float(rag_result.get("confidence", 0.0))
    except requests.exceptions.Timeout:
        error = "RAG timeout"
        logger.warning("RAG timeout | user=%s", user_id)
    except requests.exceptions.ConnectionError:
        error = "RAG unavailable"
        logger.warning("RAG unavailable | user=%s", user_id)
    except Exception as exc:
        error = str(exc)
        logger.error("RAG error | user=%s error=%s", user_id, exc, exc_info=True)

    # ── Step 4: routing decision (D-04: threshold 60%) ──
    if error is not None:
        # RAG unavailable → escalate so staff can follow up;
        # also send fallback message to patient via responder
        routing_decision = "rag_error"
    elif confidence is not None and confidence < ESCALATION_THRESHOLD:
        routing_decision = "escalation"
    else:
        routing_decision = "rag_response"

    elapsed = time.time() - start_ts
    logger.info(
        "Routing | user=%s intent=%s confidence=%.2f decision=%s elapsed=%.3fs",
        user_id,
        intent,
        confidence if confidence is not None else -1.0,
        routing_decision,
        elapsed,
    )

    result = _build_result(
        user_id=user_id,
        routing_decision=routing_decision,
        intent=intent,
        confidence=confidence,
        rag_result=rag_result,
        error=error,
    )
    result["reply_token"] = reply_token

    # ── Step 5: hand off to responder ──
    try:
        from services.line_responder import send_response  # lazy import
        send_response(result)
    except Exception as exc:
        logger.error(
            "Responder error | user=%s error=%s", user_id, exc, exc_info=True
        )

    return result


# ── Helpers ───────────────────────────────────────────────────────

def _build_result(
    *,
    user_id: str,
    routing_decision: str,
    intent: str,
    confidence: float | None,
    rag_result: dict | None,
    error: str | None,
) -> dict:
    return {
        "user_id": user_id,
        "routing_decision": routing_decision,
        "intent": intent,
        "confidence": confidence,
        "rag_result": rag_result,
        "error": error,
    }
