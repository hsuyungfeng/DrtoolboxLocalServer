"""
LINE Bot Integration Tests — Task 8

Validates Tasks 5-7 end-to-end with mock LINE API and mock RAG.

Test scenarios:
  1. Normal: message → RAG (confidence 80%) → response sent (<5s)
  2. Escalation: message → RAG (confidence 45%) → no auto-reply (<5s)
  3. RAG error: message → fallback message sent (<5s)
  4. LINE API error: retry logic works, or failure is logged
  5. Signature validation: invalid sig → 400; valid sig → 200
  6. Abusive message → auto escalation
  7. Empty / verification event → 200 OK

SC-2 gate: assert 100% of messages processed within 5 seconds.
"""

import base64
import hashlib
import hmac
import json
import os
import sys
import time
from unittest.mock import MagicMock, patch

import pytest

# ── Path setup ─────────────────────────────────────────────────────
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

# ── Import modules under test ──────────────────────────────────────
from api.routes.line_bot import _parse_event, _verify_signature
from services.message_router import _classify_intent, route_message
from services.line_responder import _format_rag_response, send_response, FALLBACK_MESSAGE


# ─────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────

@pytest.fixture()
def flask_client():
    """Minimal Flask test client with LINE blueprint registered."""
    os.environ.setdefault("LINE_CHANNEL_SECRET", "test_secret_abc123")
    os.environ.setdefault("LINE_CHANNEL_ACCESS_TOKEN", "")

    from api.app import create_app
    app = create_app({"TESTING": True})
    with app.test_client() as client:
        yield client


def _make_signature(secret: str, body: bytes) -> str:
    digest = hmac.new(secret.encode(), body, hashlib.sha256).digest()
    return base64.b64encode(digest).decode()


def _line_event(text: str = "Hi doctor", user_id: str = "Uabc123") -> dict:
    return {
        "events": [
            {
                "type": "message",
                "replyToken": "reply_token_001",
                "source": {"type": "user", "userId": user_id},
                "message": {"type": "text", "id": "msg001", "text": text},
            }
        ]
    }


def _rag_ok(confidence: float = 0.80) -> dict:
    return {
        "answer": "Take ibuprofen 400 mg every 8 hours with food.",
        "confidence": confidence,
        "citations": [{"document_name": "formulary.pdf", "page_number": 12}],
        "query_time_ms": 50.0,
    }


# ─────────────────────────────────────────────────────────────────
# Unit: Signature validation
# ─────────────────────────────────────────────────────────────────

class TestSignatureValidation:
    def test_valid_signature(self):
        secret = "test_secret"
        body = b'{"events": []}'
        sig = _make_signature(secret, body)
        assert _verify_signature(secret, body, sig) is True

    def test_invalid_signature(self):
        secret = "test_secret"
        body = b'{"events": []}'
        assert _verify_signature(secret, body, "bad_signature") is False

    def test_tampered_body(self):
        secret = "test_secret"
        original = b'{"events": []}'
        sig = _make_signature(secret, original)
        tampered = b'{"events": [1]}'
        assert _verify_signature(secret, tampered, sig) is False


# ─────────────────────────────────────────────────────────────────
# Unit: Message parsing
# ─────────────────────────────────────────────────────────────────

class TestMessageParsing:
    def test_parse_text_event(self):
        event = {
            "type": "message",
            "replyToken": "rtoken",
            "source": {"type": "user", "userId": "U123"},
            "message": {"type": "text", "id": "m1", "text": "Hello"},
        }
        env = _parse_event(event)
        assert env is not None
        assert env["user_id"] == "U123"
        assert env["text"] == "Hello"
        assert env["message_type"] == "text"

    def test_parse_image_event(self):
        event = {
            "type": "message",
            "replyToken": "rtoken",
            "source": {"userId": "U456"},
            "message": {"type": "image", "id": "img001"},
        }
        env = _parse_event(event)
        assert env is not None
        assert env["text"] == "[IMAGE]"
        assert env["image_id"] == "img001"

    def test_skip_non_message_event(self):
        event = {"type": "follow", "source": {"userId": "U789"}}
        assert _parse_event(event) is None

    def test_parse_returns_received_at(self):
        event = {
            "type": "message",
            "source": {"userId": "U001"},
            "message": {"type": "text", "text": "hi"},
        }
        before = time.time()
        env = _parse_event(event)
        assert env["received_at"] >= before


# ─────────────────────────────────────────────────────────────────
# Unit: Intent classification
# ─────────────────────────────────────────────────────────────────

class TestIntentClassification:
    def test_medical_query(self):
        assert _classify_intent("What is the treatment for fever?") == "medical_query"

    def test_appointment(self):
        assert _classify_intent("I want to make an appointment") == "appointment"

    def test_medication(self):
        assert _classify_intent("What dose of medication should I take?") == "medication"

    def test_greeting(self):
        assert _classify_intent("Hello doctor") == "greeting"

    def test_abusive(self):
        assert _classify_intent("You stupid idiot") == "abusive"

    def test_general(self):
        assert _classify_intent("What are your office hours?") == "general"


# ─────────────────────────────────────────────────────────────────
# Unit: RAG response formatting
# ─────────────────────────────────────────────────────────────────

class TestFormatRagResponse:
    def test_adds_citations(self):
        result = _rag_ok(0.85)
        text = _format_rag_response(result)
        assert "formulary.pdf" in text
        assert "Sources" in text or "來源" in text

    def test_no_citations_no_footer(self):
        result = {"answer": "Take rest.", "confidence": 0.9, "citations": []}
        text = _format_rag_response(result)
        assert text == "Take rest."

    def test_empty_answer_returns_fallback(self):
        text = _format_rag_response({"answer": "", "confidence": 0.7})
        assert text == FALLBACK_MESSAGE

    def test_deduplicates_citations(self):
        result = {
            "answer": "Rest and hydrate.",
            "confidence": 0.8,
            "citations": [
                {"document_name": "guide.pdf"},
                {"document_name": "guide.pdf"},
            ],
        }
        text = _format_rag_response(result)
        assert text.count("guide.pdf") == 1


# ─────────────────────────────────────────────────────────────────
# Integration: Normal flow (confidence >= 60%) — SC-2 gate
# ─────────────────────────────────────────────────────────────────

class TestNormalFlow:
    @patch("services.message_router.ConversationManager")
    @patch("services.message_router.requests.post")
    @patch("services.line_responder._push_message", return_value=True)
    def test_high_confidence_routes_to_response(self, mock_push, mock_rag_post, mock_conv_mgr):
        mock_rag_post.return_value = MagicMock(
            status_code=200,
            json=lambda: _rag_ok(0.80),
            raise_for_status=lambda: None,
        )

        envelope = {
            "user_id": "U001",
            "reply_token": "rtoken",
            "text": "What are the symptoms of diabetes?",
            "received_at": time.time(),
            "message_type": "text",
        }
        start = time.time()
        result = route_message(envelope)
        elapsed = time.time() - start

        assert result["routing_decision"] == "rag_response"
        assert result["confidence"] == pytest.approx(0.80)
        assert elapsed < 5.0, f"SC-2 VIOLATION: took {elapsed:.3f}s"

    @patch("services.message_router.ConversationManager")
    @patch("services.message_router.requests.post")
    @patch("services.line_responder._push_message", return_value=True)
    def test_sc2_latency_100_percent(self, mock_push, mock_rag_post, mock_conv_mgr):
        """SC-2 gate: 100% of messages processed within 5 seconds."""
        mock_rag_post.return_value = MagicMock(
            status_code=200,
            json=lambda: _rag_ok(0.75),
            raise_for_status=lambda: None,
        )

        messages = [
            "What is hypertension?",
            "How to manage diabetes?",
            "Cough treatment",
            "Fever management",
            "Medication side effects",
        ]
        violations = []
        for msg in messages:
            envelope = {
                "user_id": "U_latency",
                "reply_token": "r",
                "text": msg,
                "received_at": time.time(),
                "message_type": "text",
            }
            start = time.time()
            route_message(envelope)
            elapsed = time.time() - start
            if elapsed >= 5.0:
                violations.append((msg, elapsed))

        assert violations == [], (
            f"SC-2 VIOLATIONS: {len(violations)}/{len(messages)} messages exceeded 5s: {violations}"
        )


# ─────────────────────────────────────────────────────────────────
# Integration: Escalation flow (confidence < 60%) — SC-2 gate
# ─────────────────────────────────────────────────────────────────

class TestEscalationFlow:
    @patch("services.message_router.ConversationManager")
    @patch("services.message_router.EscalationHandler")
    @patch("services.message_router.requests.post")
    @patch("services.line_responder._push_message", return_value=True)
    def test_low_confidence_escalates(self, mock_push, mock_rag_post, mock_esc_handler, mock_conv_mgr):
        mock_rag_post.return_value = MagicMock(
            status_code=200,
            json=lambda: _rag_ok(0.45),
            raise_for_status=lambda: None,
        )

        envelope = {
            "user_id": "U002",
            "reply_token": "rtoken2",
            "text": "Something unusual about my condition",
            "received_at": time.time(),
            "message_type": "text",
        }
        start = time.time()
        result = route_message(envelope)
        elapsed = time.time() - start

        assert result["routing_decision"] == "escalation"
        assert result["confidence"] == pytest.approx(0.45)
        # Escalation should NOT push a message to patient
        mock_push.assert_not_called()
        assert elapsed < 5.0, f"SC-2 VIOLATION: escalation took {elapsed:.3f}s"

    @patch("services.message_router.ConversationManager")
    @patch("services.message_router.EscalationHandler")
    def test_abusive_message_auto_escalates(self, mock_esc_handler, mock_conv_mgr):
        """Abusive messages skip RAG and go straight to escalation."""
        with patch("services.line_responder.send_response", return_value=True):
            envelope = {
                "user_id": "U_abuse",
                "reply_token": "r",
                "text": "You stupid idiot doctor",
                "received_at": time.time(),
                "message_type": "text",
            }
            result = route_message(envelope)
        assert result["routing_decision"] == "escalation"
        assert result["intent"] == "abusive"


# ─────────────────────────────────────────────────────────────────
# Integration: RAG error → fallback message
# ─────────────────────────────────────────────────────────────────

class TestRagErrorFlow:
    @patch("services.message_router.ConversationManager")
    @patch("services.message_router.requests.post", side_effect=Exception("Connection refused"))
    @patch("services.line_responder._push_message", return_value=True)
    def test_rag_error_sends_fallback(self, mock_push, mock_rag_post, mock_conv_mgr):
        envelope = {
            "user_id": "U003",
            "reply_token": "rtoken3",
            "text": "What medication should I take?",
            "received_at": time.time(),
            "message_type": "text",
        }
        start = time.time()
        result = route_message(envelope)
        elapsed = time.time() - start

        assert result["routing_decision"] == "rag_error"
        assert result["error"] is not None
        # Fallback push should have been attempted
        mock_push.assert_called_once()
        assert elapsed < 5.0, f"SC-2 VIOLATION: RAG error path took {elapsed:.3f}s"

    @patch("services.line_responder.ConversationManager")
    @patch("services.line_responder.requests.post")
    def test_send_response_fallback_on_rag_error(self, mock_line_post, mock_conv_mgr):
        mock_line_post.return_value = MagicMock(status_code=200)
        os.environ["LINE_CHANNEL_ACCESS_TOKEN"] = "test_token"

        routing_result = {
            "user_id": "U003",
            "routing_decision": "rag_error",
            "rag_result": None,
            "confidence": None,
            "error": "Connection refused",
        }
        ok = send_response(routing_result)
        assert ok is True

        assert mock_line_post.called, "requests.post should have been called"
        call_kwargs = mock_line_post.call_args
        # call_args is a Call object: (args, kwargs) — json is a kwarg
        sent_text = call_kwargs.kwargs["json"]["messages"][0]["text"]
        assert sent_text == FALLBACK_MESSAGE

        os.environ.pop("LINE_CHANNEL_ACCESS_TOKEN", None)


# ─────────────────────────────────────────────────────────────────
# Integration: LINE API retry logic
# ─────────────────────────────────────────────────────────────────

class TestLineApiRetry:
    def test_retries_on_500(self):
        """Retry on 5xx, succeed on third attempt."""
        call_count = {"n": 0}

        def fake_post(*args, **kwargs):
            call_count["n"] += 1
            mock = MagicMock()
            mock.status_code = 500 if call_count["n"] < 3 else 200
            return mock

        from services import line_responder
        os.environ["LINE_CHANNEL_ACCESS_TOKEN"] = "tok"

        with patch("services.line_responder.requests.post", side_effect=fake_post):
            with patch("services.line_responder.time.sleep"):  # skip actual sleep
                ok = line_responder._push_message("U_retry", "test message")

        assert ok is True
        assert call_count["n"] == 3
        os.environ.pop("LINE_CHANNEL_ACCESS_TOKEN", None)

    def test_gives_up_after_max_retries(self):
        """After MAX_RETRIES failures, return False."""
        from services import line_responder
        os.environ["LINE_CHANNEL_ACCESS_TOKEN"] = "tok"

        with patch("services.line_responder.requests.post",
                   return_value=MagicMock(status_code=500)):
            with patch("services.line_responder.time.sleep"):
                ok = line_responder._push_message("U_fail", "test")

        assert ok is False
        os.environ.pop("LINE_CHANNEL_ACCESS_TOKEN", None)


# ─────────────────────────────────────────────────────────────────
# Webhook endpoint (Flask integration)
# ─────────────────────────────────────────────────────────────────

class TestWebhookEndpoint:
    def test_empty_events_returns_200(self, flask_client):
        body = json.dumps({"events": []}).encode()
        secret = os.environ.get("LINE_CHANNEL_SECRET", "test_secret_abc123")
        sig = _make_signature(secret, body)

        resp = flask_client.post(
            "/api/line/webhook",
            data=body,
            content_type="application/json",
            headers={"X-Line-Signature": sig},
        )
        assert resp.status_code == 200

    def test_invalid_signature_returns_400(self, flask_client):
        body = json.dumps({"events": []}).encode()
        resp = flask_client.post(
            "/api/line/webhook",
            data=body,
            content_type="application/json",
            headers={"X-Line-Signature": "bad_sig"},
        )
        assert resp.status_code == 400

    def test_valid_message_event_returns_200(self, flask_client):
        payload = _line_event("Hello doctor", "U_test_01")
        body = json.dumps(payload).encode()
        secret = os.environ.get("LINE_CHANNEL_SECRET", "test_secret_abc123")
        sig = _make_signature(secret, body)

        with patch("api.routes.line_bot._dispatch_background"):
            resp = flask_client.post(
                "/api/line/webhook",
                data=body,
                content_type="application/json",
                headers={"X-Line-Signature": sig},
            )
        assert resp.status_code == 200

    def test_health_endpoint(self, flask_client):
        resp = flask_client.get("/api/line/health")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "ok"
        assert "line_channel_secret_configured" in data


# ─────────────────────────────────────────────────────────────────
# SC-2 summary test
# ─────────────────────────────────────────────────────────────────

class TestSC2Compliance:
    """
    SC-2 Acceptance Gate: 100% of messages processed within 5 seconds.

    This test drives 10 distinct message types through the routing +
    response pipeline with mocked external calls and asserts that no
    message exceeds the 5-second SLA.
    """

    @patch("services.message_router.ConversationManager")
    @patch("services.message_router.requests.post")
    @patch("services.line_responder._push_message", return_value=True)
    def test_all_messages_within_5s(self, mock_push, mock_rag, mock_conv_mgr):
        mock_rag.return_value = MagicMock(
            status_code=200,
            json=lambda: _rag_ok(0.80),
            raise_for_status=lambda: None,
        )

        test_cases = [
            ("U01", "What are the symptoms of hypertension?"),
            ("U02", "How do I manage my diabetes medication?"),
            ("U03", "I have a fever and cough"),
            ("U04", "When should I come for my next appointment?"),
            ("U05", "What are the side effects of aspirin?"),
            ("U06", "I need to reschedule my appointment"),
            ("U07", "How do I take my medication?"),
            ("U08", "Is it safe to take two pills?"),
            ("U09", "My stomach hurts after eating"),
            ("U10", "Hello, I have a question"),
        ]

        violations = []
        for user_id, text in test_cases:
            envelope = {
                "user_id": user_id,
                "reply_token": "r",
                "text": text,
                "received_at": time.time(),
                "message_type": "text",
            }
            start = time.time()
            route_message(envelope)
            elapsed = time.time() - start
            if elapsed >= 5.0:
                violations.append((user_id, text[:30], round(elapsed, 3)))

        total = len(test_cases)
        passed = total - len(violations)
        pass_pct = passed / total * 100

        assert violations == [], (
            f"SC-2 FAILED: {len(violations)}/{total} messages ({100-pass_pct:.0f}%) "
            f"exceeded 5s SLA:\n{violations}"
        )
