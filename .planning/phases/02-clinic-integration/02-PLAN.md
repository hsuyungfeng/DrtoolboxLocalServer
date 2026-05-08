---
phase: 02-clinic-integration
plan: complete
subsystem: HIS Database + LINE Communication
tags: [HIS, LINE, RAG-Router, ConversationHistory]
dependency_graph:
  requires:
    - 01-foundation (Phase 1 complete)
  provides:
    - HIS integration + LINE messaging
  affects:
    - Phase 3 (Web Forms + Unified Inbox)
tech_stack:
  - SQLite (HIS + clinic.db)
  - LINE Messaging API
  - Flask (Blueprint routing)
  - ChromaDB (existing RAG)
key_files:
  created:
    - src/api/routes/line_bot.py
    - src/services/his_query.py
    - src/services/conversation_manager.py
    - schema/patient_conversations_table.sql
    - tests/test_line_integration.py
  modified:
    - src/api/app.py (register LINE webhook)
    - schema/clinic.db.sql (add conversation history table)
    - src/api/routes/rag.py (add confidence scoring for escalation)
decisions:
  - D-01: Query queue + retry for HIS failures (handle IT instability)
  - D-02: 1-hour TTL caching for common HIS queries
  - D-03: LINE messages default route to RAG (medical knowledge)
  - D-04: Auto-escalate to staff when RAG confidence < 60%
  - D-05: Patient queries use RAG generically (no proactive HIS lookup)
  - D-06: 1-week conversation history per patient
  - D-07: Escalations include full conversation history context
metrics:
  duration: ~2-3 weeks
  tasks: 12
  estimated_completion: 2026-05-29
---

# Phase 2 Plan: 診所整合 (Clinic Integration)

## 一行描述
Phase 2 連接本地診所 HIS 資料庫和 LINE 患者通訊，實現智能訊息路由（RAG 查詢或人工升級）與患者對話歷史管理。

---

## ✅ 成功標準 (Success Criteria Checklist)

From ROADMAP.md Phase 2 — all are verification gates:

- [ ] **SC-1**: HIS read-only connection stable with no data leaks
- [ ] **SC-2**: LINE bot responds to 100% of incoming messages within 5 seconds
- [ ] **SC-3**: Query results cached; repeat queries <100ms
- [ ] **SC-4**: Conversation history accurate and retrievable

---

## 📋 Task Breakdown

Tasks are sequenced for parallel work where safe. Group by functional area.

### Group A: HIS Database Integration (Tasks 1-4)

**Task 1: HIS Connection Module & Query Queue**
- **Purpose**: Establish read-only HIS connection with resilience against IT downtime
- **Deliverable**: `src/services/his_query.py`
- **Acceptance Criteria**:
  - Opens read-only connection to local HIS database (clinic IT provides schema/credentials)
  - Implements query queue (D-01): buffers queries if HIS unavailable
  - Implements exponential backoff retry (3 retries, max 10s)
  - Connection pooling to avoid exhausting HIS resources
  - Logs all connection failures for debugging
- **Estimate**: M
- **Blockers**: HIS database schema + connection credentials from clinic IT
- **Related Decisions**: D-01

**Task 2: HIS Query Caching Layer**
- **Purpose**: Cache frequent clinic queries for sub-100ms performance
- **Deliverable**: Cache logic in `src/services/his_query.py` + Redis or SQLite cache backend
- **Acceptance Criteria**:
  - Caches common queries (patient info, appointments, medication history) with 1-hour TTL (D-02)
  - Cache hit/miss metrics logged
  - Cache invalidation on data update (optional: poll HIS for schema changes)
  - Repeat queries return cached result in <100ms
- **Estimate**: M
- **Depends on**: Task 1
- **Related Decisions**: D-02

**Task 3: HIS Analytical Query Wrapper**
- **Purpose**: Expose common clinic queries as reusable functions
- **Deliverable**: Query wrappers in `src/services/his_query.py` (get_patient_info, get_appointments, get_medication_history, etc.)
- **Acceptance Criteria**:
  - At least 5 common queries implemented with type-safe return types
  - All queries use caching layer from Task 2
  - Error handling for missing records (patient not found)
  - Unit tests for each query (mock HIS responses)
- **Estimate**: S
- **Depends on**: Task 1, Task 2
- **Related Requirements**: DB-01, DB-02

**Task 4: HIS Integration Tests & Monitoring**
- **Purpose**: Verify HIS connectivity and performance under normal/degraded conditions
- **Deliverable**: `tests/test_his_integration.py` + monitoring dashboard
- **Acceptance Criteria**:
  - Integration tests with mock HIS (use SQLite test DB with sample clinic data)
  - Tests for normal operation, connection failure, slow response, query timeout
  - Performance test: repeat queries cached <100ms
  - Monitoring: logs connection status, cache hit rate, query latency
  - Success Criterion SC-1 & SC-3 verified
- **Estimate**: M
- **Depends on**: Task 1, Task 2, Task 3
- **Related Requirements**: DB-01, DB-02, DB-03

---

### Group B: LINE Bot Integration (Tasks 5-8)

**Task 5: LINE Webhook Endpoint & Message Parsing**
- **Purpose**: Accept incoming LINE messages and parse user intent
- **Deliverable**: `src/api/routes/line_bot.py` + Flask Blueprint
- **Acceptance Criteria**:
  - POST /api/line/webhook receives LINE Events API messages
  - Parses message type (text, image, etc.) and user ID
  - Validates LINE signature (uses LINE channel secret)
  - Implements retry handler for failed deliveries (LINE expects 200 OK within 3s)
  - Logs all incoming messages for audit trail
  - Registers Blueprint in src/api/app.py
- **Estimate**: M
- **Blockers**: LINE channel ID, channel secret (clinic provides)
- **Related Decisions**: D-03
- **Related Requirements**: COMM-01

**Task 6: Message Routing Logic (RAG vs. Escalation)**
- **Purpose**: Classify incoming patient messages and route to appropriate handler
- **Deliverable**: `src/services/message_router.py`
- **Acceptance Criteria**:
  - Uses hybrid query intent classification (reuse logic from scripts/hybrid_query.py)
  - Default route: send to RAG (D-03)
  - RAG returns response + confidence score
  - If confidence < 60% (D-04), flag for escalation instead of sending to patient
  - Logs routing decision and confidence score for all queries
  - Edge case: malformed/abusive messages → automatic escalation
- **Estimate**: M
- **Depends on**: Task 5 (needs RAG query infrastructure)
- **Related Decisions**: D-03, D-04
- **Related Requirements**: COMM-02

**Task 7: LINE Response Sender & Error Handling**
- **Purpose**: Send RAG responses back to patient via LINE, with fallbacks for errors
- **Deliverable**: `src/services/line_responder.py`
- **Acceptance Criteria**:
  - Sends response message to patient via LINE Messaging API
  - Includes source citations (from RAG) when available
  - If RAG unavailable, sends "We're having trouble. Staff will follow up soon."
  - Retries failed sends (LINE API transient failures)
  - Logs all outbound messages
  - All responses sent within 5 seconds of incoming message (SC-2)
- **Estimate**: S
- **Depends on**: Task 6
- **Related Requirements**: COMM-02

**Task 8: LINE Integration Tests & Response Time Validation**
- **Purpose**: Verify LINE bot end-to-end with response time SLA
- **Deliverable**: `tests/test_line_integration.py`
- **Acceptance Criteria**:
  - Mock LINE API (simulate incoming messages)
  - Test normal flow: patient message → RAG query → response sent
  - Test escalation flow: low-confidence message → escalation instead of send
  - Performance test: verify 100% of responses sent in <5 seconds (SC-2)
  - Test error handling: RAG unavailable, LINE API down
  - Success Criterion SC-2 verified
- **Estimate**: M
- **Depends on**: Task 5, Task 6, Task 7
- **Related Requirements**: COMM-01, COMM-02

---

### Group C: Conversation History & Escalation (Tasks 9-12)

**Task 9: Conversation History Schema & Database**
- **Purpose**: Store patient messages and responses for 1 week (D-06)
- **Deliverable**: `schema/patient_conversations_table.sql` + migration
- **Acceptance Criteria**:
  - New table: `patient_conversations` (patient_id, message_id, sender, text, timestamp, rag_confidence, escalated_flag)
  - Add to clinic.db.sql schema
  - Create migration script to add table to existing clinic.db
  - Implement 1-week TTL deletion (D-06): cron job or Flask command to purge rows older than 7 days
  - Indexes on patient_id, timestamp for fast retrieval
  - Test: insert 100 messages, verify TTL cleanup works
- **Estimate**: S
- **Depends on**: None (foundational)
- **Related Decisions**: D-06

**Task 10: Conversation Manager Service**
- **Purpose**: Encapsulate conversation history CRUD operations
- **Deliverable**: `src/services/conversation_manager.py`
- **Acceptance Criteria**:
  - Methods: save_message(patient_id, sender, text, confidence, escalated)
  - Methods: get_conversation_history(patient_id, days=7)
  - Methods: cleanup_old_conversations() (triggered by cron)
  - All operations logged (audit trail)
  - Handles concurrent writes (thread-safe)
  - Unit tests with mock database
- **Estimate**: S
- **Depends on**: Task 9
- **Related Decisions**: D-06

**Task 11: Escalation Handler & Staff Notification**
- **Purpose**: When RAG confidence < 60%, escalate to clinic staff with full context
- **Deliverable**: `src/services/escalation_handler.py`
- **Acceptance Criteria**:
  - On escalation, create escalation record with:
    - Patient ID, original message, RAG confidence score
    - Full conversation history (last 7 days) (D-07)
    - Escalation timestamp
  - Route escalations to clinic staff (integration point TBD: email, dashboard, or queue)
  - Log all escalations for audit
  - Staff can mark escalation as resolved
  - Resolved escalations logged with resolution notes
  - Unit tests with sample low-confidence scenarios
- **Estimate**: M
- **Depends on**: Task 6, Task 10
- **Related Decisions**: D-04, D-07
- **Related Requirements**: COMM-02, COMM-03

**Task 12: Conversation History Retrieval & Patient Privacy**
- **Purpose**: Allow clinic staff to view patient conversation history; ensure privacy
- **Deliverable**: API endpoints in `src/api/routes/line_bot.py`
- **Acceptance Criteria**:
  - GET /api/patient/{patient_id}/conversations — returns 7-day history (staff only)
  - Requires authentication (clinic staff login, TBD in Phase 3)
  - Returns patient name, messages, RAG responses, escalations
  - Logs all access to conversation history (audit trail)
  - Success Criterion SC-4 verified (history accurate & retrievable)
  - Privacy: no storage of sensitive HIS data in conversations (D-05)
  - Unit tests with sample conversations
- **Estimate**: S
- **Depends on**: Task 9, Task 10
- **Related Decisions**: D-05, D-06, D-07
- **Related Requirements**: COMM-03

---

## 🏗️ Architecture & Integration Points

Phase 2 builds on Phase 1 (LLM + RAG) by adding:

### HIS Integration Alongside RAG
```
Patient Query (LINE)
  ↓
Message Router (Tasks 5-6)
  ├→ Intent = RAG Query
  │    ↓
  │   RAG Query (Phase 1)
  │    ↓
  │   Confidence Score (Task 6)
  │    ├→ Confidence >= 60% → Send Response (Task 7)
  │    └→ Confidence < 60% → Escalate (Task 11)
  │
  └→ Intent = HIS Query
       ↓
      HIS Connection (Task 1)
       ↓
      Cache Check (Task 2)
       ├→ Cache Hit → Return Cached (Task 2)
       └→ Cache Miss → Query HIS (Task 1)
```

### Data Flow
1. **Patient Message**: LINE Webhook (Task 5) receives message
2. **Intent Routing**: Message Router (Task 6) classifies intent
3. **RAG or HIS**: Route to appropriate service
4. **Confidence Check**: RAG confidence < 60% → escalate (Task 11)
5. **Response**: Send to patient (Task 7) or escalate to staff (Task 11)
6. **History**: Log all messages in clinic.db (Task 10)

### Reusable Assets from Phase 1
- **`src/api/routes/rag.py`**: Already provides confidence scoring → reuse for escalation threshold
- **`scripts/hybrid_query.py`**: Intent classification logic → reuse for message routing
- **`src/api/app.py`**: Flask app structure → register LINE Blueprint here
- **`schema/clinic.db.sql`**: Extend with conversation history table (Task 9)

### New Flask Blueprint
```python
# src/api/routes/line_bot.py
@line_bp.route('/api/line/webhook', methods=['POST'])
def webhook():
    # Task 5: Parse LINE event
    # Task 6: Route message
    # Task 7: Send response or escalate
    # Task 10: Log conversation
```

---

## 🔧 Decision Checkpoints

All 7 decisions from 02-CONTEXT.md are locked and validated:

1. **D-01 (HIS Resilience)**: Query queue + retry in `src/services/his_query.py` (Task 1)
   - Clinic IT can be unstable → queue buffers queries, exponential backoff retries
   - Escalate to staff if HIS remains down >30s

2. **D-02 (HIS Caching)**: 1-hour TTL for common queries (Task 2)
   - Common queries: patient info, appointments, medication history
   - Cache invalidation: manual purge or TTL-based cleanup

3. **D-03 (LINE Default Route)**: All messages default to RAG (Task 6)
   - "What is high blood pressure?" → RAG medical knowledge
   - No proactive HIS lookup unless user explicitly asks about their record

4. **D-04 (Escalation Threshold)**: Confidence < 60% → escalate (Task 6, Task 11)
   - Safety critical: avoid low-confidence medical advice
   - Staff handles uncertain queries

5. **D-05 (Patient Privacy)**: No proactive HIS lookup (Task 6)
   - Patient queries use generic RAG knowledge
   - Patient-specific medical history only if staff provides context (Phase 3+)

6. **D-06 (Conversation TTL)**: 1-week history per patient (Task 9)
   - Long enough for multi-turn conversations
   - Short enough for privacy (automatic deletion)

7. **D-07 (Escalation Context)**: Full 7-day conversation included in escalations (Task 11)
   - Staff gets complete patient interaction history
   - Better context for human follow-up

---

## ⚠️ Risk & Mitigation

| Risk | Mitigation | Task |
|------|-----------|------|
| HIS connection failure | Query queue + retry (D-01), fallback to cached results | Task 1 |
| HIS slow responses | Cache common queries (D-02), timeout + escalate | Task 2 |
| LINE API rate limits | Batch responses, retry with backoff | Task 7 |
| Low RAG confidence | Auto-escalate to staff (D-04), staff reviews escalations | Task 6, Task 11 |
| Message routing errors | Unit tests (Task 8), audit logs, manual review | Task 6, Task 8 |
| Conversation history data loss | Database backup (clinic IT), integrity checks | Task 9, Task 10 |
| Privacy violations | 1-week TTL deletion (D-06), no sensitive HIS storage (D-05) | Task 9 |
| Response time SLA miss | Performance testing (Task 8), optimize RAG queries | Task 8 |

---

## 📦 Deliverables Mapping

| ROADMAP Deliverable | Tasks | Files |
|--------|-------|-------|
| HIS database connection module | 1, 2, 3 | `src/services/his_query.py` |
| LINE bot integration and message routing | 5, 6, 7 | `src/api/routes/line_bot.py`, `src/services/message_router.py`, `src/services/line_responder.py` |
| Conversation history storage and retrieval | 9, 10, 12 | `schema/patient_conversations_table.sql`, `src/services/conversation_manager.py` |
| Performance monitoring for queries | 4, 8 | `tests/test_his_integration.py`, `tests/test_line_integration.py` |

---

## 🚀 Execution Notes

### Prerequisites (Before Starting)
- [ ] Clinic IT provides HIS database credentials + schema documentation
- [ ] Clinic IT provides HIS database access (read-only user account)
- [ ] LINE channel ID and channel secret obtained from LINE Messaging API console
- [ ] Verify Phase 1 is 100% complete (all 4 plans done, RAG engine running)

### Execution Order
1. **Tasks 1-4** (HIS Integration): Can start immediately once HIS credentials obtained
2. **Tasks 9-10** (Conversation History): Can run in parallel with Tasks 1-4 (no dependencies)
3. **Tasks 5-8** (LINE Bot): Can start once Tasks 1-4 foundational work done
4. **Tasks 11-12** (Escalation & Retrieval): Final integration (depends on Tasks 5-10)

### Testing Strategy
- **Unit tests**: All services tested with mocks (no live HIS or LINE API)
- **Integration tests**: Use test HIS database (SQLite) + LINE Messaging API sandbox
- **E2E test**: Single patient conversation flow (message → RAG → response → history)
- **Load test**: 100+ concurrent patients, verify <5s response time

### Documentation
- Update `docs/clinic_user_guide.md` with LINE bot usage
- Add HIS query documentation for clinic staff
- Document escalation workflow for staff

---

## ✔️ Verification Gates (Pre-Execution)

All success criteria are **testable** and **measurable**:

- **SC-1** (HIS Stability): Integration tests (Task 4) verify no data loss, stable connections
- **SC-2** (LINE <5s): Load test (Task 8) measures response time for 100+ messages
- **SC-3** (Cache <100ms): Performance test (Task 4) verifies cached repeat queries
- **SC-4** (History Retrievable): Unit tests (Tasks 9, 10, 12) verify CRUD operations

---

*Phase 2 Plan created: 2026-05-08*  
*Status: Ready for Execution*  
*Next: Assign tasks to executor agents or start Task 1*
