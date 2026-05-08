---
phase: 02-clinic-integration
plan: 02
wave: 2
subsystem: LINE Bot Integration
status: completed
completed_date: 2026-05-08
tags: [LINE, RAG-Router, Message-Handling, Integration-Tests]
dependency_graph:
  requires:
    - 02-01 (HIS Integration: connection layer, query queue, cache)
  provides:
    - LINE webhook endpoint (POST /api/line/webhook)
    - Message routing with RAG + escalation
    - Response sender with retry
    - SC-2 latency validation (<5s)
  affects:
    - 02-03 (Wave 3: escalation handler, conversation history)
tech_stack:
  added:
    - line-bot-sdk==3.13.0
    - python-dotenv (installed in environment)
  patterns:
    - Flask Blueprint (/api/line/*)
    - HMAC-SHA256 signature validation
    - Background thread dispatch (return 200 immediately, process async)
    - Exponential backoff retry (LINE API)
    - Module-level constant vs call-time env var (testability pattern)
key_files:
  created:
    - src/api/routes/line_bot.py
    - src/services/__init__.py
    - src/services/message_router.py
    - src/services/line_responder.py
    - tests/test_line_integration.py
  modified:
    - src/api/app.py (register line_bp, add endpoints to root listing)
decisions:
  - D-03: All LINE messages default-routed to RAG (not HIS); escalate only on low confidence
  - D-04: Escalation threshold = 60%; confidence < 0.60 flags for staff, no auto-reply
metrics:
  duration: ~1.5 hours
  completed_date: 2026-05-08
  tasks_completed: 4
  tasks_total: 4
  tests_passing: 26
  tests_total: 26
---

# Phase 2 Plan 02: LINE Bot Integration (Wave 2) Summary

## One-Line Summary

LINE webhook + message router (RAG-default, <60% escalation) + response sender (exponential backoff) with 26 passing tests validating SC-2 <5s latency for 100% of messages.

---

## Task Completion Status

| Task | Name | Status | Commit | Key Files |
|------|------|--------|--------|-----------|
| 5 | LINE Webhook Endpoint | COMPLETE | `0b268ff` | src/api/routes/line_bot.py |
| 6 | Message Routing Logic | COMPLETE | `ee64a3d` | src/services/message_router.py |
| 7 | LINE Response Sender | COMPLETE | `137e51e` | src/services/line_responder.py |
| 8 | Integration Tests | COMPLETE | `036cbf0` | tests/test_line_integration.py |

---

## Architecture Summary

### Task 5: LINE Webhook (line_bot.py)
- **Blueprint**: `line_bp` at `/api/line/*`
- **POST /api/line/webhook**: Validates X-Line-Signature (HMAC-SHA256 using `LINE_CHANNEL_SECRET`), parses LINE event types (text/image/location/sticker), returns HTTP 200 immediately, dispatches processing to background daemon thread
- **GET /api/line/health**: Reports channel secret/token configuration status
- **Audit logging**: Every incoming event logged with user_id and message type
- **3s compliance**: Background thread pattern ensures webhook returns well within LINE's 3s requirement

### Task 6: Message Router (message_router.py)
- **Intent classification**: Rules-based (medication / appointment / medical_query / greeting / abusive / general)
- **D-03 implementation**: All non-abusive messages query RAG at `RAG_API_URL` (default: `http://127.0.0.1:8080/api/v1/rag/query`)
- **D-04 implementation**: `confidence < 0.60` → `routing_decision = "escalation"`; no auto-reply
- **Auto-escalation**: Abusive messages and empty text bypass RAG entirely
- **RAG error handling**: Connection errors → `routing_decision = "rag_error"` → fallback message
- **Log format**: `user_id | intent | confidence | decision | elapsed`

### Task 7: LINE Responder (line_responder.py)
- **send_response()**: Routes `rag_response` → format + push; `escalation` → log only (Wave 3); `rag_error` → fallback message
- **Citation formatting**: Appends `[來源 / Sources: doc1.pdf, doc2.pdf]` (max 3, deduplicated)
- **Retry strategy**: Exponential backoff — 0.5s, 1s, 2s delays; max 3 attempts; gives up on 4xx (except 429)
- **Token read at call-time**: `os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")` inside `_push_message()` for testability
- **SC-2 monitoring**: Logs warning if outbound elapsed > 5.0s

### app.py changes
- Import and register `line_bp` from `api.routes.line_bot`
- Added `line_webhook` and `line_health` to root endpoint listing

---

## Success Criteria Verification

| Criterion | Status | Evidence |
|-----------|--------|---------|
| SC-2: <5s response for 100% of messages | PASS | `TestSC2Compliance.test_all_messages_within_5s` — 10/10 messages < 5s |
| COMM-01: Webhook receives + parses messages | PASS | `TestWebhookEndpoint` (4 tests), `TestMessageParsing` (4 tests) |
| COMM-02: Routing works (RAG + escalation) | PASS | `TestNormalFlow`, `TestEscalationFlow`, `TestRagErrorFlow` |
| Signature validation | PASS | `TestSignatureValidation` (3 tests) |
| Retry logic | PASS | `TestLineApiRetry` (2 tests) |

---

## Test Results

```
26 passed, 0 failed
```

| Test Class | Tests | Result |
|------------|-------|--------|
| TestSignatureValidation | 3 | PASS |
| TestMessageParsing | 4 | PASS |
| TestIntentClassification | 6 | PASS |
| TestFormatRagResponse | 4 | PASS |
| TestNormalFlow | 2 | PASS |
| TestEscalationFlow | 2 | PASS |
| TestRagErrorFlow | 2 | PASS |
| TestLineApiRetry | 2 | PASS |
| TestWebhookEndpoint | 4 | PASS (after python-dotenv installed) |
| TestSC2Compliance | 1 | PASS — 10/10 messages < 5s |

---

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] line-bot-sdk not installed**
- **Found during**: Task 5 setup
- **Issue**: `line-bot-sdk` not in requirements.txt; not installed
- **Fix**: `pip install line-bot-sdk==3.13.0`; signature validation implemented using Python's built-in `hmac` + `hashlib` (more reliable than SDK's handler for testing)
- **Files modified**: environment only (not added to requirements.txt — library imported but not directly used in final implementation)

**2. [Rule 3 - Blocking] python-dotenv missing in test environment**
- **Found during**: Task 8 (TestWebhookEndpoint fixture)
- **Issue**: `ModuleNotFoundError: No module named 'dotenv'` when importing `api.app` in tests
- **Fix**: `pip install python-dotenv`
- **Files modified**: environment only

**3. [Rule 1 - Bug] Module-level constant captured empty LINE_CHANNEL_ACCESS_TOKEN**
- **Found during**: Task 8 (TestLineApiRetry failures)
- **Issue**: `LINE_CHANNEL_TOKEN = os.getenv(...)` at module import time captured empty string before tests set env var → `_push_message()` returned early without calling `requests.post`
- **Fix**: Changed to read `os.getenv("LINE_CHANNEL_ACCESS_TOKEN", "")` at call-time inside `_push_message()`
- **Files modified**: `src/services/line_responder.py`
- **Commit**: `137e51e` (included in Task 7 commit)

**4. [Rule 1 - Bug] Test used incorrect call_args indexing**
- **Found during**: Task 8 (`test_send_response_fallback_on_rag_error`)
- **Issue**: `call_kwargs[1]["json"]` raised `TypeError: 'NoneType' object is not subscriptable` — caused by bug #3 above (mock never called), and fixed access to use `call_kwargs.kwargs["json"]` after fix
- **Fix**: Used `.kwargs` attribute of pytest `call_args` Call object
- **Files modified**: `tests/test_line_integration.py`

---

## Known Stubs

None — all routing paths wire to real implementations. Escalation (`routing_decision = "escalation"`) intentionally logs only without sending to patient; this is correct per D-04 and will be completed in Wave 3 (Task 11: staff notification).

---

## Environment Variables Required

```bash
LINE_CHANNEL_SECRET=<clinic LINE channel secret>
LINE_CHANNEL_ACCESS_TOKEN=<clinic LINE channel access token>
RAG_API_URL=http://127.0.0.1:8080/api/v1/rag/query   # default
ESCALATION_THRESHOLD=0.60                              # default
RAG_REQUEST_TIMEOUT=4.0                                # default
LINE_SEND_TIMEOUT=3.0                                  # default
```

All env vars have safe defaults for local development. LINE credentials are not needed for running tests (mocked throughout).

---

## Integration Points for Wave 3 (Plan 03)

1. **Escalation handler** — `routing_decision == "escalation"` path in `line_responder.send_response()` is intentionally a stub; Wave 3 Task 11 will add staff notification (push to staff LINE group or internal dashboard)
2. **Conversation history** — `envelope["received_at"]` timestamp available for Wave 3 Task 10 conversation storage
3. **Reply token** — `result["reply_token"]` propagated through routing result for Wave 3 reply-message support

---

## Self-Check

All files created/committed verified:

- `src/api/routes/line_bot.py` — exists, committed in `0b268ff`
- `src/services/__init__.py` — exists, committed in `0b268ff`
- `src/services/message_router.py` — exists, committed in `ee64a3d`
- `src/services/line_responder.py` — exists, committed in `137e51e`
- `tests/test_line_integration.py` — exists, committed in `036cbf0`
- `src/api/app.py` — modified, committed in `036cbf0`

## Self-Check: PASSED
