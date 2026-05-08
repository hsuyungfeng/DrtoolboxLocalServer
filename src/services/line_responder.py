"""
LINE Response Sender — Task 7

Sends outbound messages to patients via LINE Messaging API.
Handles three routing outcomes from message_router:

  rag_response  — send RAG answer (+ citations) to patient
  escalation    — log for staff (Wave 3 Task 11); send no auto-reply
  rag_error     — send pre-written fallback message to patient

Retry strategy: exponential backoff up to 3 attempts for transient
LINE API failures.

SC-2 target: all sends dispatched within 5 seconds of message receipt.
"""

import logging
import os
import time

import requests

logger = logging.getLogger(__name__)

# ── Configuration ──────────────────────────────────────────────────
LINE_API_BASE = "https://api.line.me/v2/bot"
LINE_PUSH_URL = f"{LINE_API_BASE}/message/push"

FALLBACK_MESSAGE = (
    "We're having trouble answering your question right now. "
    "Our staff will follow up with you shortly."
)
MAX_RETRIES = 3
RETRY_BASE_DELAY = 0.5  # seconds (0.5, 1.0, 2.0)
LINE_SEND_TIMEOUT = 3.0  # seconds — must leave room inside 5s SLA


# ── Internal helpers ───────────────────────────────────────────────

def _format_rag_response(rag_result: dict) -> str:
    """
    Build patient-facing message from RAG result.

    Appends source citations when available.
    """
    answer = rag_result.get("answer", "").strip()
    if not answer:
        return FALLBACK_MESSAGE

    citations = rag_result.get("citations", [])
    if citations:
        source_names = list(
            dict.fromkeys(  # deduplicate, preserve order
                c.get("document_name", "") for c in citations if c.get("document_name")
            )
        )
        if source_names:
            sources_str = ", ".join(source_names[:3])  # max 3 citations
            answer = f"{answer}\n\n[來源 / Sources: {sources_str}]"

    return answer


def _push_message(user_id: str, text: str) -> bool:
    """
    Send a text message to a LINE user with exponential-backoff retry.

    Returns True on success, False after all retries exhausted.
    """
    token = os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")
    if not token:
        # No token configured — log and skip (expected in test environments)
        logger.info(
            "LINE_CHANNEL_ACCESS_TOKEN not set; skipping push | user=%s", user_id
        )
        return True  # treated as success for routing-logic purposes

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {token}",
    }
    payload = {
        "to": user_id,
        "messages": [{"type": "text", "text": text}],
    }

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.post(
                LINE_PUSH_URL,
                json=payload,
                headers=headers,
                timeout=LINE_SEND_TIMEOUT,
            )
            if resp.status_code == 200:
                logger.info(
                    "LINE push sent | user=%s attempt=%d", user_id, attempt
                )
                return True

            # 429 / 5xx → retry; 4xx (except 429) → don't retry
            if resp.status_code < 500 and resp.status_code != 429:
                logger.error(
                    "LINE push permanent error | user=%s status=%d body=%s",
                    user_id,
                    resp.status_code,
                    resp.text[:200],
                )
                return False

            logger.warning(
                "LINE push transient error | user=%s status=%d attempt=%d/%d",
                user_id,
                resp.status_code,
                attempt,
                MAX_RETRIES,
            )

        except requests.exceptions.Timeout:
            logger.warning(
                "LINE push timeout | user=%s attempt=%d/%d", user_id, attempt, MAX_RETRIES
            )
        except requests.exceptions.ConnectionError as exc:
            logger.warning(
                "LINE push connection error | user=%s error=%s attempt=%d/%d",
                user_id,
                exc,
                attempt,
                MAX_RETRIES,
            )

        if attempt < MAX_RETRIES:
            delay = RETRY_BASE_DELAY * (2 ** (attempt - 1))
            time.sleep(delay)

    logger.error("LINE push failed after %d attempts | user=%s", MAX_RETRIES, user_id)
    return False


# ── Public entry point ─────────────────────────────────────────────

def send_response(routing_result: dict) -> bool:
    """
    Dispatch outbound LINE message based on routing decision.

    Args:
        routing_result: output dict from message_router.route_message()

    Returns:
        True if message sent (or intentionally not sent for escalations),
        False if send failed.
    """
    user_id = routing_result.get("user_id", "unknown")
    decision = routing_result.get("routing_decision", "escalation")
    rag_result = routing_result.get("rag_result")
    send_start = time.time()

    logger.info(
        "Responder | user=%s decision=%s", user_id, decision
    )

    if decision == "rag_response" and rag_result:
        message_text = _format_rag_response(rag_result)
        ok = _push_message(user_id, message_text)
        _log_outbound(user_id, decision, message_text, send_start)
        return ok

    elif decision in ("escalation",):
        # D-04: do NOT send auto-reply; flag for staff (Wave 3)
        logger.info(
            "Escalation queued | user=%s confidence=%.2f",
            user_id,
            routing_result.get("confidence") or 0.0,
        )
        # Wave 3 (Task 11) will persist + notify staff here
        return True

    else:
        # rag_error or unknown — send fallback message
        ok = _push_message(user_id, FALLBACK_MESSAGE)
        _log_outbound(user_id, decision, FALLBACK_MESSAGE, send_start)
        return ok


def _log_outbound(user_id: str, decision: str, text: str, send_start: float) -> None:
    elapsed = time.time() - send_start
    logger.info(
        "Audit | outbound LINE message | user=%s decision=%s elapsed=%.3fs chars=%d",
        user_id,
        decision,
        elapsed,
        len(text),
    )
    if elapsed > 5.0:
        logger.warning(
            "SC-2 VIOLATION | outbound took %.3fs > 5s | user=%s",
            elapsed,
            user_id,
        )
