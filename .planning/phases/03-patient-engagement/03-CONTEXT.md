# Phase 3: Patient Engagement — Web Forms & Multi-Channel Communication - Context

**Gathered:** 2026-05-08  
**Status:** Ready for planning

<domain>
## Phase Boundary

Enable patient intake through web forms with automatic HIS database population, and provide staff with a unified inbox for managing LINE patient messages. Phase 3 focuses on **internal clinic operations** — patient-facing web intake and staff communication management.

**In scope:**
- Patient intake web form (demographics, medical history, appointment booking)
- Automatic HIS database population from form submissions
- Patient record dashboard (view-only for patients, editable for staff)
- Unified staff inbox aggregating LINE messages by patient
- Message routing: patient ID matching across intake forms and LINE messages

**Out of scope (deferred to Phase 4+):**
- doctor-toolbox.com/chats integration (web-based patient chat) — will connect in future phase
- Multi-language support — assume Traditional Chinese for Phase 3
- Advanced patient personalization — defer to Phase 4+ after core flows work

</domain>

<decisions>
## Implementation Decisions

### Patient Intake Form Strategy
- **D-01:** Form captures core demographics (name, phone, email, date of birth) + medical intake (chief complaint, medication list, allergies, appointment type). Keep initial form lean; extensible for clinic-specific fields later.
- **D-02:** Form validation: required fields enforced client-side (UX feedback) + server-side (security). Phone/email format validation. Date of birth must be past date.
- **D-03:** Form submission handling: POST to `/api/patient/intake` endpoint. Returns 201 with patient_id. Idempotent via phone+email uniqueness check — duplicate submission returns existing patient_id (prevents duplicate records).

### HIS Auto-Population Strategy
- **D-04:** Form submissions INSERT directly into clinic.db patient table. No approval workflow for Phase 3 (clinic staff handles validation later via dashboard edit).
- **D-05:** Conflict resolution: If phone+email combination already exists in HIS, UPDATE that record with new form data (merge strategy). Log all updates for audit trail.
- **D-06:** Appointment booking from form: Create entry in clinic.db appointments table with status='pending'. Staff approves/schedules in dashboard.

### Patient Dashboard Design
- **D-07:** Patient view (patient-facing): Shows own record (name, contact, medical summary, upcoming appointments, conversation history with bot). Read-only, non-editable.
- **D-08:** Staff view (staff-facing): Shows full patient record + edit capability (demographics, medical history, appointments, notes). Dashboard for all patients searchable by name/phone/patient_id.
- **D-09:** Performance target: Patient dashboard loads in <1s (cached patient record, lazy-load conversation history). Pagination for large patient lists.

### Unified Staff Inbox for LINE
- **D-10:** Staff inbox aggregates all patient LINE messages. View defaults to unread-first, grouped by patient. Show patient name, last message timestamp, unread count, escalation status.
- **D-11:** Message context: Clicking a patient opens conversation history (last 7 days from patient_conversations table). Staff can reply directly to LINE messages from inbox.
- **D-12:** Escalation handling: Messages marked as escalation in LINE flow appear in inbox with visual indicator (e.g., red badge). Escalation context (RAG confidence, original message) displayed.
- **D-13:** Notification strategy: Simple approach for Phase 3 — inbox auto-refreshes every 3-5 seconds (polling). Real-time WebSocket deferred to Phase 4.

### Message Routing & Patient Matching
- **D-14:** Patient ID matching: LINE messages include user_id from LINE (unique per LINE user). Create mapping table: line_user_id → patient_id (one-to-one, created during intake or first LINE interaction).
- **D-15:** Web form to LINE matching: Patient provides phone/email in intake form. Staff can manually link that form submission to existing LINE user_id in dashboard. No automatic matching (avoids privacy issues).
- **D-16:** Fallback lookup: If patient_id not found in mapping, staff dashboard offers "Link LINE user" button to associate LINE_user_id with patient record.

### Technology Stack (Informed by Codebase)
- **Frontend:** Flask templates (Jinja2) for simplicity. Extend existing src/api/app.py Blueprint pattern. Use HTML forms + minimal JavaScript (no SPA framework in Phase 3).
- **Backend:** Extend existing Flask routes in src/api/routes/. Reuse SQLite clinic.db schema patterns. Pydantic for request validation (already used in codebase).
- **Database:** clinic.db extended with tables: patient (if not exists), appointments, line_user_mapping, patient_conversations (already created in Phase 2).
- **Styling:** Bootstrap 5 (lightweight, responsive, clinic-appropriate). Existing src/static/ directory for CSS.

### Claude's Discretion
- Field validation rules (min/max lengths, regex patterns) — researcher/planner will determine based on clinic requirements
- Dashboard UI layout specifics (single-page vs multi-section) — designer/planner will refine based on wireframes
- Polling interval for inbox refresh (3-5s default, may tune based on load testing)
- Patient dashboard edit permissions (which staff roles can edit) — clinic policy question for Phase 3 planning

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase Requirements & Vision
- `.planning/ROADMAP.md` §Phase 3 — Complete phase goal, success criteria, deliverables
- `.planning/REQUIREMENTS.md` — Requirements WEB-01, WEB-02, WEB-03, COMM-04, COMM-05 (note: COMM-04/05 deferred to Phase 4+)
- `.planning/PROJECT.md` — Project vision, clinic context, local-first principles

### Prior Phase Context (Locked Decisions)
- `.planning/phases/02-clinic-integration/02-CONTEXT.md` — Phase 2 decisions on HIS integration, LINE routing, escalation, conversation history (inherited by Phase 3)

### Codebase Architecture & Patterns
- `src/api/app.py` — Flask application structure, Blueprint registration pattern for routes
- `src/api/routes/` — Existing API endpoint patterns (hybrid.py, clinic_his.py, line_bot.py) to follow for consistency
- `schema/clinic.db.sql` — Database schema; Phase 3 extends this with patient intake table and line_user_mapping
- `src/services/conversation_manager.py` — Conversation history retrieval (Phase 2) — reuse for dashboard

### Integration Points
- Phase 2's LINE webhook + routing system feeds into Phase 3's unified inbox
- Phase 2's conversation_manager.get_conversation_history() feeds into patient dashboard
- Phase 2's escalation_handler integration — escalations appear in staff inbox

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Flask Blueprint structure** (`src/api/routes/hybrid.py`, `clinic_his.py`): Established pattern for modular endpoints. Phase 3 creates `src/api/routes/patient_intake.py` following same structure.
- **Pydantic validation** (existing codebase): Already using Pydantic for request validation. Extend for intake form validation (PatientIntakeRequest model).
- **clinic.db schema** (`schema/clinic.db.sql`): Extensible SQLite schema. Add `patients` table, `line_user_mapping`, `appointments` tables.
- **Conversation history** (`src/services/conversation_manager.py`): Phase 2 already provides get_conversation_history(). Reuse directly in dashboard.
- **HIS query patterns** (`scripts/hybrid_query.py`): Query caching + error handling patterns. Reuse for patient dashboard queries.

### Established Patterns
- **Error handling:** Try/except with structured logging (used throughout src/api/routes/). Follow for new endpoints.
- **Authentication stub:** Phase 2 uses X-Staff-ID header. Extend for dashboard staff access (Phase 3 simple check; Phase 4 integrates clinic staff login).
- **Database operations:** SQLite context managers, thread-safe access via RLock (conversation_manager.py). Reuse pattern for patient intake CRUD.

### Integration Points
- **LINE webhook** → Patient intake form: When new patient first messages, check line_user_mapping. If not found, suggest intake form link in LINE bot response.
- **Patient intake endpoint** → clinic.db: Form submissions INSERT patient, create appointment, create line_user_mapping entry if phone matches existing LINE user.
- **Staff dashboard** → conversation_manager: Dashboard retrieves history for display. Uses existing service (no new code).
- **Escalation display** → staff inbox: Escalation records from Phase 2 appear in inbox with escalation indicator. Reuse escalation_handler output.

</code_context>

<specifics>
## Specific Ideas

- **Intake form UX:** Single-page form, progress indicator for multi-section forms (demographics → medical history → appointment booking). Submit button disabled until all required fields filled.
- **Patient dashboard search:** Name prefix search (e.g., "王*" finds all Wang patients). Phone number search (last 4 digits or full number).
- **Staff inbox notifications:** Browser notification when new message arrives (via browser Notification API if staff grants permission). Fallback: visual inbox badge count.
- **Dashboard caching:** Patient list cached for 5 minutes to avoid repeated HIS queries. Manual "refresh" button for staff to force reload.

</specifics>

<deferred>
## Deferred Ideas

- **doctor-toolbox.com/chats integration** — Originally planned for Phase 3. Deferred to Phase 4+ to keep Phase 3 focused on internal intake + inbox. Will connect API later.
- **Real-time message sync (WebSocket)** — Phase 3 uses polling for staff inbox. Phase 4+ upgrade to WebSocket/SSE for real-time updates.
- **Multi-language support** — Phase 3 assumes Traditional Chinese. Multi-language support (English, Simplified Chinese) deferred to Phase 4+.
- **Advanced patient personalization** — Integrating HIS patient records into RAG context deferred to Phase 4 (Phase 3 keeps RAG + patient data separate for privacy).
- **Voice-based intake** — Speech-to-text for form input deferred to Phase 2+ (v2 requirement).
- **Patient appointment self-service** — Phase 3 intake creates appointments in pending status. Self-service appointment booking deferred to Phase 4+.

</deferred>

---

*Phase: 03-patient-engagement*  
*Context gathered: 2026-05-08*
