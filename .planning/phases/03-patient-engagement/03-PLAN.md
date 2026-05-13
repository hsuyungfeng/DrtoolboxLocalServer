# Phase 3: Patient Engagement — Implementation Plan

## Phase Overview

**Objective:** Deliver patient intake web forms with automatic HIS database population, patient record dashboards, and a unified staff inbox for managing LINE messages.

**Success Criteria:**
1. Web form collects patient intake data securely (demographics + medical history)
2. Form submissions auto-populate clinic.db without data loss
3. Patient dashboard displays current records with <1s load time
4. Staff inbox aggregates LINE messages by patient with 3-5s refresh polling
5. Manual LINE-to-form linking workflow operational (privacy-preserving)
6. Message routing accurate across all channels (no dropped messages)
7. Escalation indicators visible in staff inbox

**Locked Decisions:** All 16 decisions in CONTEXT.md (D-01 through D-16) are implemented exactly as specified. No alternatives or simplifications.

---

## Implementation Structure

Phase 3 groups into **4 functional layers** with clear dependencies:

1. **Database Layer** (D-04, D-05, D-06, D-14, D-15, D-16) — Schema extensions
2. **API Layer** (D-01, D-02, D-03) — Form endpoints + validation
3. **Dashboard Layer** (D-07, D-08, D-09) — Patient & staff dashboards
4. **Inbox Layer** (D-10, D-11, D-12, D-13) — Staff message aggregation & polling

All layers reuse Phase 2 assets (conversation history, escalation handler, LINE routing).

---

## Task Breakdown & Dependencies

### WAVE 1: Database Schema & Validation Models (Foundational)

**Task 1.1: Extend clinic.db Schema for Patient Intake**

- **Path:** `schema/clinic.db.sql`
- **Deliverable:**
  - ADD `patients` table (patient_id PK, name, phone, email, dob, medical_history, allergies, created_at, updated_at, updated_by)
  - ADD `appointments` table (appointment_id PK, patient_id FK, appointment_date, status, created_at, updated_at, updated_by)
  - ADD `line_user_mapping` table (mapping_id PK, line_user_id UNIQUE, patient_id FK, created_at, linked_by)
  - ADD indices: `idx_patients_phone_email` (UNIQUE composite for deduplication), `idx_patients_created`, `idx_appointments_patient`, `idx_line_user_mapping_patient`
  - ADD audit columns: `created_by`, `updated_by`, `created_at`, `updated_at` to existing tables
  
- **Acceptance Criteria:**
  - Schema runs on existing clinic.db without errors
  - All tables created with proper constraints
  - Phone+email uniqueness enforced (per D-03 idempotency)
  - Foreign keys enabled globally (PRAGMA)
  - Indexes created for performance (query planning)
  
- **Owner:** Database layer
- **Dependency:** None (foundational)
- **Implements:** D-04 (direct insert), D-05 (phone+email uniqueness), D-06 (appointment table), D-14 (line_user_mapping), D-15 (manual linking), D-16 (fallback lookup)

---

**Task 1.2: Create Pydantic Validation Models for Patient Intake**

- **Path:** `src/api/models/patient_intake.py` (NEW)
- **Deliverable:**
  - `PatientIntakeRequest` model: name, phone, email, dob, chief_complaint, medications, allergies, appointment_date, appointment_type
  - `PatientDemographics` model: name, phone, email, dob (subset for dashboard)
  - `AppointmentRequest` model: appointment_date, appointment_type, notes
  - `LineUserMapping` model: line_user_id, patient_id
  - Validation rules: required fields enforced, phone format (Taiwan standard), email format, dob must be past date, appointment_date >= today, chief_complaint max 500 chars
  - Per D-01: "lean form" — name, phone, email, dob, chief_complaint, medications, allergies, appointment_type only
  - Per D-02: client-side feedback messages + server-side rejection
  
- **Acceptance Criteria:**
  - All models instantiate without errors
  - Invalid inputs raise `ValidationError` (Pydantic standard)
  - Phone validation accepts Taiwan formats (09XX-XXX-XXX, 09XXXXXXXX)
  - Email validation per RFC standards
  - DOB validation rejects future dates
  - All models serialize to JSON for API responses
  
- **Owner:** API layer
- **Dependency:** Task 1.1 (schema must exist)
- **Implements:** D-01 (form fields), D-02 (validation logic)

---

### WAVE 2: Patient Intake API Endpoint

**Task 2.1: Implement POST /api/patient/intake Endpoint**

- **Path:** `src/api/routes/patient_intake.py` (NEW)
- **Deliverable:**
  - Flask Blueprint `patient_intake_bp` registered in `src/api/app.py`
  - POST `/api/patient/intake` accepts `PatientIntakeRequest` JSON
  - Validation: Pydantic validation + server-side phone/email format checks
  - Idempotency: Query `patients` table by phone+email before insert. If exists, return 200 with existing patient_id (D-03)
  - INSERT flow (if new):
    1. Insert into `patients` table (name, phone, email, dob, chief_complaint, medications, allergies, created_at, updated_by='system')
    2. Insert into `appointments` table (patient_id, appointment_date, status='pending', created_at, updated_by='system')
    3. Log all inserts to audit trail (file or database) — per D-05 audit requirement
  - Return: 201 Created with `{patient_id, message: "Intake form submitted"}` or 200 OK with `{patient_id, message: "Patient already exists"}`
  - Error handling:
    - 400: Validation error (missing required fields, format invalid)
    - 409: Database conflict (unlikely due to UNIQUE constraint, but handle gracefully)
    - 500: Database error (log full error, return generic message to client)
  
- **Acceptance Criteria:**
  - Valid form submission creates patient + appointment
  - Duplicate phone+email returns existing patient_id (idempotency)
  - All form fields stored in database
  - Audit log records all INSERTs with timestamp + updated_by
  - Response includes patient_id usable by dashboard
  - cURL test: `curl -X POST /api/patient/intake -H "Content-Type: application/json" -d '{"name":"王小明", ...}' | jq .patient_id`
  
- **Owner:** API layer
- **Dependency:** Task 1.1 (schema), Task 1.2 (validation models)
- **Implements:** D-01 (form fields collected), D-02 (validation), D-03 (idempotency, 201/200 responses)

---

**Task 2.2: Implement Conflict Resolution for HIS Updates (D-05)**

- **Path:** `src/services/patient_service.py` (NEW)
- **Deliverable:**
  - `PatientService` class with method `upsert_patient(demographics, medical_history)`
  - Logic: If patient exists by phone+email, UPDATE with new medical_history + chief_complaint, log update with old_values/new_values
  - If new, INSERT and return patient_id
  - Audit trail: Log all UPDATEs with staff_id (from D-05: "updated_by" column tracks who made change)
  - Database: Use SQLite transactions (ROLLBACK on error)
  - Error handling: Lock contention (retry with exponential backoff), constraint violations (log and return 409)
  
- **Acceptance Criteria:**
  - New patient: INSERT succeeds, audit trail records insert
  - Duplicate phone+email: UPDATE merges new data, audit trail records old_values and new_values
  - Concurrent requests: No race conditions (transaction isolation)
  - Test: Upsert same patient twice → verify second call updates, not duplicates
  
- **Owner:** API layer (service tier)
- **Dependency:** Task 1.1 (schema with updated_by/created_at), Task 2.1 (patient intake endpoint uses this)
- **Implements:** D-05 (conflict resolution strategy)

---

### WAVE 3: Patient & Staff Dashboards

**Task 3.1: Patient Dashboard — View-Only Patient Record**

- **Path:** `src/api/routes/patient_dashboard.py` (NEW), `src/templates/patient_dashboard.html` (NEW)
- **Deliverable:**
  - GET `/api/patient/<patient_id>` JSON endpoint: Returns `{name, phone, email, dob, medical_summary, upcoming_appointments, conversation_history_snippet}`
  - Frontend: Flask Jinja2 template showing patient's own record
  - Data displayed:
    - Demographics: name, contact, DOB
    - Medical summary: chief_complaint, medications, allergies (from intake form)
    - Upcoming appointments: Next 3 appointments from `appointments` table, status='pending' or 'approved'
    - Conversation history snippet: Last 3 messages from `patient_conversations` (reuse Phase 2 conversation_manager)
  - View-only: No edit buttons, no staff functions
  - Per D-07: Dashboard is read-only for patients
  - Performance: Cache patient record for 5 minutes (per D-09 <1s load target). Use Redis or in-memory dict keyed by patient_id with TTL.
  
- **Acceptance Criteria:**
  - Patient sees their own data only (patient_id path parameter matches authenticated patient)
  - Page loads in <1s (measure with browser DevTools)
  - Conversation history accurate (matches Phase 2 escalation handler output)
  - No HIS patient data leaked (only form-submitted data + bot responses)
  - Test: Curl `/api/patient/123` → verify response includes all expected fields
  
- **Owner:** Dashboard layer
- **Dependency:** Task 1.1 (patients table), Phase 2 conversation_manager (reuse for history)
- **Implements:** D-07 (patient view), D-09 (performance caching)

---

**Task 3.2: Staff Dashboard — Full CRUD Patient Records**

- **Path:** `src/api/routes/staff_dashboard.py` (NEW), `src/templates/staff_dashboard.html` (NEW)
- **Deliverable:**
  - GET `/api/staff/patients` JSON endpoint: List all patients, paginated (20 per page), searchable by name/phone/patient_id
  - GET `/api/staff/patients/<patient_id>` JSON endpoint: Full record (demographics, medical history, appointments, conversation history, escalations)
  - POST `/api/staff/patients/<patient_id>` JSON endpoint: UPDATE patient record (demographics, medical history, appointment status)
  - Authentication: X-Staff-ID header (per Phase 2 stub; Phase 4 upgrades to clinic auth)
  - Frontend: HTML table with pagination, search box, edit modal for each patient
  - Edit capability: Staff can modify name, phone, email, DOB, medical history, appointment status (pending→approved→completed)
  - Escalation indicator: Show escalation flag + context from Phase 2 escalation_handler (red badge if escalation=true)
  - Conversation history: Display full 7-day history with timestamps, sender (patient/bot), confidence scores
  
- **Acceptance Criteria:**
  - Staff authenticated via X-Staff-ID header
  - Patient list paginated, searchable
  - Search by name prefix (王*), phone (last 4 digits), patient_id
  - Full patient record editable (except patient_id, created_at)
  - Appointment status transitionable (pending→approved→completed)
  - Escalation flag visible with context
  - Test: POST X-Staff-ID header, search for patient, edit record, verify update in database
  
- **Owner:** Dashboard layer
- **Dependency:** Task 1.1 (patients + appointments tables), Task 2.2 (PatientService.upsert_patient for updates), Phase 2 (escalation_handler, conversation_manager)
- **Implements:** D-08 (staff view), D-09 (search + pagination for performance), D-12 (escalation indicator)

---

### WAVE 4: Patient-to-LINE Linking & Inbox Aggregation

**Task 4.1: Patient-to-LINE Mapping API**

- **Path:** `src/api/routes/patient_line_linking.py` (NEW)
- **Deliverable:**
  - POST `/api/staff/link-line-user` endpoint: Accept `{line_user_id, patient_id}`, insert into `line_user_mapping` table
  - Per D-15: Manual staff action only (no automatic matching for privacy)
  - Per D-16: Fallback lookup — dashboard shows "Link LINE User" button if patient has no mapping
  - GET `/api/staff/patient/<patient_id>/line-status` endpoint: Check if patient has LINE mapping; return `{linked: bool, line_user_id: string|null}`
  - Authentication: X-Staff-ID header required
  - Validation: line_user_id format check, patient_id must exist, ensure one-to-one relationship (line_user_id is UNIQUE in mapping table)
  
- **Acceptance Criteria:**
  - Staff can link LINE user to patient
  - Duplicate line_user_id rejected (UNIQUE constraint)
  - Unlinking possible (DELETE from mapping) via staff action
  - Test: POST link request, verify patient can now receive LINE messages routed by patient_id
  
- **Owner:** API layer + Inbox layer
- **Dependency:** Task 1.1 (line_user_mapping schema), Task 3.2 (staff dashboard integrated with linking UI)
- **Implements:** D-14 (patient_id matching), D-15 (manual linking), D-16 (fallback lookup with dashboard button)

---

**Task 4.2: Staff Inbox Aggregation & Polling**

- **Path:** `src/api/routes/staff_inbox.py` (NEW), `src/templates/staff_inbox.html` (NEW)
- **Deliverable:**
  - GET `/api/staff/inbox` JSON endpoint: List all patients with unread messages, sorted by last_message_timestamp DESC
  - Response format:
    ```json
    [
      {
        "patient_id": 123,
        "patient_name": "王小明",
        "last_message": "我的血壓偏高怎麼辦？",
        "last_message_timestamp": "2026-05-11T14:30:00Z",
        "unread_count": 2,
        "escalation_flag": true,
        "escalation_context": "RAG confidence 0.45 < 60% threshold"
      }
    ]
    ```
  - Per D-10: Unread-first, grouped by patient, show patient name + last message + unread count + escalation badge
  - Frontend: HTML inbox view with patient list, click to open conversation
  - Frontend: JavaScript polling every 3-5 seconds (configurable via env var INBOX_POLL_INTERVAL_SECONDS, default 5)
  - Per D-13: Simple polling (WebSocket deferred to Phase 4)
  
- **Acceptance Criteria:**
  - Inbox lists all patients with unread LINE messages
  - Sorting: Unread first, then by last_message_timestamp DESC
  - Escalation badge shows when escalation_flag=true
  - Frontend polling updates inbox every 3-5s without full page reload
  - Test: Send LINE message, wait 5s, verify message appears in inbox
  
- **Owner:** Inbox layer
- **Dependency:** Task 1.1 (patient_conversations table from Phase 2), Task 4.1 (patient_id lookup via line_user_mapping), Phase 2 (escalation_handler for escalation_flag)
- **Implements:** D-10 (aggregation + sorting), D-13 (polling interval)

---

**Task 4.3: Conversation Thread View in Staff Inbox**

- **Path:** `src/api/routes/staff_inbox.py` (continuation), `src/templates/staff_inbox_thread.html` (NEW)
- **Deliverable:**
  - GET `/api/staff/patient/<patient_id>/conversation-thread` JSON endpoint: Retrieve 7-day conversation history for patient (per Phase 2 D-06)
  - Response: Array of messages `[{timestamp, sender, text, rag_confidence, escalated_flag}, ...]`
  - Per D-11: Clicking patient in inbox opens this thread view
  - Reuse Phase 2 `conversation_manager.get_conversation_history(patient_id)` (already implemented)
  - Frontend: Display conversation as chat-like thread (patient message, bot response, staff notes if any)
  - Staff reply capability (if time permits in Wave): Staff can compose reply to post back to LINE (use Phase 2 LINE API)
  
- **Acceptance Criteria:**
  - Thread shows all messages for past 7 days
  - Messages sorted by timestamp ASC (oldest first)
  - Escalation flag visible on escalated messages (red highlight)
  - RAG confidence visible for bot responses
  - Test: Open patient conversation, verify all messages from Phase 2 appear, escalations marked
  
- **Owner:** Inbox layer
- **Dependency:** Task 1.1 (patient_conversations table from Phase 2), Task 4.2 (inbox aggregation router), Phase 2 (conversation_manager, escalation_handler)
- **Implements:** D-11 (message context), D-12 (escalation context)

---

### WAVE 5: Integration Tests & Smoke Tests

**Task 5.1: Integration Test Suite**

- **Path:** `tests/test_patient_intake_integration.py` (NEW)
- **Deliverable:**
  - Test scenario 1: New patient form submission → verify patient created, appointment pending, audit logged
  - Test scenario 2: Duplicate phone+email submission → verify idempotency (return existing patient_id, no duplicate)
  - Test scenario 3: Patient dashboard access → verify read-only view, no HIS data, <1s load
  - Test scenario 4: Staff dashboard access → verify full record editable, search works, escalation flag shows
  - Test scenario 5: LINE-to-patient linking → verify staff links LINE user, lookup succeeds
  - Test scenario 6: Inbox polling → verify new messages appear in <5s, escalations marked
  - Test scenario 7: End-to-end: Patient submits form → staff views in dashboard → staff links to LINE → message appears in inbox
  
- **Acceptance Criteria:**
  - All scenarios pass without errors
  - Performance: Dashboard <1s, inbox <500ms per poll
  - Idempotency verified (no duplicate patients)
  - Escalation indicators accurate
  - Audit trail complete for all operations
  
- **Owner:** Test layer
- **Dependency:** All prior tasks (database, APIs, dashboards, inbox)
- **Implements:** Phase 3 success criteria (end-to-end validation)

---

**Task 5.2: Smoke Tests & Deployment Checklist**

- **Path:** `tests/smoke_tests.py` (NEW)
- **Deliverable:**
  - Script: Check database schema exists (all tables, indices, constraints)
  - Script: Check all APIs respond (health checks on /api/patient/intake, /api/staff/patients, /api/staff/inbox)
  - Script: Check authentication (X-Staff-ID header required for staff endpoints)
  - Script: Check performance baselines (intake validation <100ms, dashboard <1s, inbox <500ms)
  - Deployment checklist:
    1. Schema migrated (clinic.db backup created)
    2. All tables created with indices
    3. All Blueprint endpoints registered in Flask app
    4. Environment variables set (INBOX_POLL_INTERVAL_SECONDS, PATIENT_CACHE_TTL_SECONDS)
    5. Conversation history reachable (Phase 2 conversation_manager working)
    6. Escalation handler accessible (Phase 2 escalation_handler working)
    7. Smoke tests pass (all health checks green)
  
- **Acceptance Criteria:**
  - All smoke tests pass before Phase 3 release
  - Deployment checklist reviewed by clinic IT
  - Rollback plan documented (schema restore, feature flag disable)
  
- **Owner:** Test layer + DevOps
- **Dependency:** All prior tasks
- **Implements:** Phase 3 readiness verification

---

## Dependency Graph

```
Wave 1 (Foundational):
  Task 1.1 (Schema) — no dependencies
  Task 1.2 (Validation models) → depends on Task 1.1

Wave 2 (API):
  Task 2.1 (POST /intake) → depends on Task 1.1, Task 1.2
  Task 2.2 (Conflict resolution) → depends on Task 1.1, Task 2.1

Wave 3 (Dashboards):
  Task 3.1 (Patient dashboard) → depends on Task 1.1, Phase 2 (conversation_manager)
  Task 3.2 (Staff dashboard) → depends on Task 1.1, Task 2.2, Phase 2 (escalation_handler, conversation_manager)

Wave 4 (Inbox):
  Task 4.1 (LINE mapping) → depends on Task 1.1, Task 3.2
  Task 4.2 (Inbox aggregation) → depends on Task 1.1, Task 4.1, Phase 2
  Task 4.3 (Thread view) → depends on Task 1.1, Task 4.2, Phase 2

Wave 5 (Testing):
  Task 5.1 (Integration tests) → depends on all prior tasks
  Task 5.2 (Smoke tests) → depends on all prior tasks
```

**Critical Path:** Task 1.1 → Task 1.2 → Task 2.1 → Task 2.2 → Task 3.2 → Task 4.2 → Task 5.1

**Parallelization Opportunities:**
- Task 3.1 can run parallel to Task 2.1 (both read from schema, no conflict)
- Task 4.1 can run parallel to Task 3.2 (different concerns, same schema)
- Task 4.2 can start after Task 4.1 completes (dependency chain)

---

## Risk & Mitigation

| Risk | Impact | Mitigation | Owner |
|------|--------|-----------|-------|
| HIS schema changes during Phase 3 | Form submission fails, patient data lost | Confirm HIS schema frozen before Phase 3 start. Test with sample data. | Clinic IT |
| Duplicate patient detection fails (phone+email) | Duplicate records created, staff confusion | Write unit test for UNIQUE constraint. Test idempotency scenario (Task 2.1). | API layer |
| LINE routing breaks after linking | Messages routed to wrong patient | Integration test for end-to-end scenario (Task 5.1 scenario 7). Verify line_user_id→patient_id lookup accuracy. | Inbox layer |
| Dashboard load time exceeds 1s | Poor UX, staff avoids dashboard | Implement caching (Task 3.1, 3.2). Load test with 10K+ patient records. Use database indices (Task 1.1). | Dashboard layer |
| Escalation flag missing in inbox | Staff misses critical messages | Verify escalation_handler output format (Phase 2). Write test for escalation indicator (Task 5.1 scenario 4). | Inbox layer |
| Concurrent staff edits cause conflicts | Data loss, conflicting updates | Use database transactions (Task 2.2). Implement optimistic locking (timestamp-based conflict detection). | API layer |
| Privacy leak: patient data in logs | GDPR/privacy violation | Sanitize logs (no patient IDs, only hashed). Audit trail records staff access only (Task 3.2). | API layer + Security |
| Polling interval too aggressive | Server overload, poor performance | Start with 5s interval (default in Task 4.2). Monitor CPU/memory. Allow tuning via env var. | DevOps + Inbox layer |
| Phase 2 conversation_manager unavailable | Dashboard / inbox broken | Dependency on Phase 2 = blocker. Confirm Phase 2 complete before Phase 3 start. | Project manager |

---

## Rollout Strategy

### Phase 3 Deployment Stages

**Stage 1: Schema Migration (Pre-Production)**
- Backup clinic.db
- Run schema migration script (Task 1.1)
- Verify all tables created, indices present
- Restore from backup if any errors

**Stage 2: API Deployment (Staging → Production)**
- Deploy patient_intake.py (Task 2.1)
- Deploy patient_service.py (Task 2.2)
- Test POST /api/patient/intake with sample data
- Verify idempotency (duplicate submission returns same patient_id)

**Stage 3: Dashboard Deployment (Staging → Production)**
- Deploy patient_dashboard.py (Task 3.1)
- Deploy staff_dashboard.py (Task 3.2)
- Test patient view (read-only), staff view (edit capability)
- Verify search + pagination work
- Verify caching reduces load time

**Stage 4: Inbox Deployment (Staging → Production)**
- Deploy patient_line_linking.py (Task 4.1)
- Deploy staff_inbox.py (Task 4.2, 4.3)
- Test inbox polling (3-5s refresh)
- Verify escalation flags show
- Verify conversation history displays

**Stage 5: Smoke Tests & Cutover (Production)**
- Run integration tests (Task 5.1)
- Run smoke tests (Task 5.2)
- Staff training on new dashboard + inbox
- Enable feature flag (if implemented)
- Monitor logs for 24 hours (phase-out period)

**Rollback Plan:**
- If critical bug found, disable feature flag or revert deployment
- Restore clinic.db from pre-migration backup
- Notify clinic IT + staff

---

## Success Metrics

### Functional Success

1. **Form Submission**
   - Acceptance: POST /api/patient/intake creates patient record + appointment
   - Measurement: Test scenario 1 passes (Task 5.1)
   - Baseline: 100% success rate for valid submissions

2. **Idempotency**
   - Acceptance: Duplicate phone+email returns existing patient_id
   - Measurement: Test scenario 2 passes (Task 5.1)
   - Baseline: 100% idempotency for duplicate submissions

3. **Patient Dashboard**
   - Acceptance: Patient sees own record (read-only) with conversation history
   - Measurement: Test scenario 3 passes, <1s load time verified
   - Baseline: <1s load time for typical patient (100 messages)

4. **Staff Dashboard**
   - Acceptance: Staff can search, view, edit patient records
   - Measurement: Test scenario 4 passes, search + pagination work
   - Baseline: Full patient list searchable in <500ms

5. **LINE Linking**
   - Acceptance: Staff can manually link LINE user to patient
   - Measurement: Test scenario 5 passes
   - Baseline: One-to-one mapping enforced (UNIQUE constraint)

6. **Inbox Aggregation**
   - Acceptance: Inbox shows all patients with unread messages, updates via polling
   - Measurement: Test scenarios 6 & 7 pass, escalation flags visible
   - Baseline: Inbox refresh <500ms, escalation accuracy 100%

### Performance Baselines

| Operation | Target | Measurement |
|-----------|--------|-------------|
| Patient intake validation | <100ms | Load test with Locust/JMeter |
| Dashboard load | <1s | Browser DevTools (DOMContentLoaded + paint) |
| Inbox aggregation | <500ms | API response time |
| Inbox polling | 3-5s refresh | JavaScript timer, verify DOM update |
| Search (patient list) | <500ms | Name/phone search query time |

### Data Integrity

1. **Audit Trail**
   - All INSERTs/UPDATEs logged with timestamp + updated_by
   - Measurement: Query audit table, verify completeness
   - Baseline: 100% of patient changes audited

2. **Privacy**
   - No HIS patient data in logs (only form-submitted data)
   - Measurement: Grep logs for sensitive info (none found)
   - Baseline: Zero privacy leaks

3. **Escalation Accuracy**
   - Escalation flags match Phase 2 escalation_handler output
   - Measurement: Compare inbox escalation flag with conversation_history.escalated_flag
   - Baseline: 100% match

---

## Implementation Notes

### Reusing Phase 2 Assets

Phase 3 builds on Phase 2 (clinic integration) without modifications:

- **conversation_manager.py**: Provides `get_conversation_history(patient_id)` — used by dashboards + inbox (Task 3.1, 3.2, 4.3)
- **escalation_handler.py**: Sets `escalated_flag` on messages — used by inbox indicator (Task 4.2, 4.3)
- **LINE routing**: Messages already route via line_user_id; Phase 3 adds patient_id lookup for dashboard aggregation (Task 4.1)

No changes to Phase 2 code. Phase 3 is purely additive.

### Technology Stack

| Component | Technology | Rationale |
|-----------|-----------|-----------|
| Frontend | Flask Jinja2 templates | Existing pattern, no SPA framework per CONTEXT.md |
| Validation | Pydantic | Already used in codebase (phase 2), strong validation |
| Database | SQLite (clinic.db) | Existing, extensible schema |
| Caching | In-memory dict + TTL | Simple, fast, suitable for Phase 3 (Redis in Phase 5 if needed) |
| Polling | JavaScript setInterval | Standard browser API, 3-5s interval |
| Authentication | X-Staff-ID header | Phase 3 stub; Phase 4 integrates clinic auth |

### File Checklist

**New Files (Phase 3):**
- `schema/clinic.db.sql` — MODIFIED (schema extensions)
- `src/api/routes/patient_intake.py` — NEW
- `src/api/routes/patient_dashboard.py` — NEW
- `src/api/routes/staff_dashboard.py` — NEW
- `src/api/routes/patient_line_linking.py` — NEW
- `src/api/routes/staff_inbox.py` — NEW
- `src/api/models/patient_intake.py` — NEW
- `src/services/patient_service.py` — NEW
- `src/templates/patient_dashboard.html` — NEW
- `src/templates/staff_dashboard.html` — NEW
- `src/templates/staff_inbox.html` — NEW
- `src/templates/staff_inbox_thread.html` — NEW
- `src/static/staff_inbox_polling.js` — NEW (polling logic)
- `tests/test_patient_intake_integration.py` — NEW
- `tests/smoke_tests.py` — NEW

**Modified Files:**
- `src/api/app.py` — Register new Blueprints (patient_intake_bp, patient_dashboard_bp, staff_dashboard_bp, patient_line_linking_bp, staff_inbox_bp)

---

## Success Verification Checklist

Before Phase 3 is considered "done", verify:

- [ ] All 16 decisions (D-01 through D-16) implemented
- [ ] Database schema migrated without errors
- [ ] All 10 tasks completed (2 database, 2 API, 2 dashboard, 3 inbox, 1 test)
- [ ] Integration test suite passes (all 7 scenarios)
- [ ] Smoke test checklist complete (9 items)
- [ ] Performance baselines met (<1s dashboard, <500ms inbox, <100ms validation)
- [ ] Privacy audit passed (no HIS data in logs, staff access logged)
- [ ] Clinic IT sign-off (schema, deployment, rollback plan reviewed)
- [ ] Staff training completed (dashboard usage, inbox polling, LINE linking)
- [ ] Production deployment successful, 24h monitoring complete

---

## Next Steps (Phase 4+)

Phase 3 unlocks Phase 4 (Intelligence Growth):

1. **Real-time Inbox (Phase 4):** Upgrade polling → WebSocket/SSE for instant message notifications
2. **Clinic Auth (Phase 4):** Replace X-Staff-ID stub with clinic staff login system
3. **Multi-language (Phase 4+):** Add English + Simplified Chinese support
4. **doctor-toolbox.com Integration (Phase 4+):** Connect web chat interface
5. **Advanced Personalization (Phase 4+):** Integrate HIS patient records into RAG context (with consent)

---

*Plan created: 2026-05-11*  
*Phase: 03-patient-engagement*  
*Decisions locked: D-01 through D-16 (CONTEXT.md)*
