# Phase 2: Hermes Agent Orchestration & Logging - Plan

## 1. Implement JSON Logging Pipeline
- **Description:** Create a logging service that stores interactions as JSONL files in `/data/logs`. This will be the foundation for future fine-tuning.
- **Files Modified:** `src/services/logger_service.py`
- **Dependencies:** None
- **Acceptance Criteria:** A function can accept a conversation payload and correctly append it to a daily JSONL file safely.

## 2. Hermes Agent Routing Logic
- **Description:** Implement the Hermes agent workflow. Create tools out of the Phase 1 `RAGEngine` methods and provide them to Hermes.
- **Files Modified:** `src/agent/hermes_router.py`, `requirements.txt`
- **Dependencies:** 1
- **Acceptance Criteria:** Hermes agent can successfully decide whether to route a query to special data or general data.

## 3. Expose API Endpoints (Web/LINE)
- **Description:** Expose the Hermes agent over a Flask API to simulate Web/LINE chat connections.
- **Files Modified:** `src/api/app.py`, `src/api/routes/chat.py`
- **Dependencies:** 2
- **Acceptance Criteria:** Sending a POST request with a query returns Hermes's response and logs the interaction to JSONL.

## 4. Verification & Testing
- **Description:** Write integration tests to ensure queries are routed and logged.
- **Files Modified:** `tests/test_hermes_routing.py`
- **Dependencies:** 3
- **Acceptance Criteria:** Tests pass verifying the JSON logging and routing behavior.
