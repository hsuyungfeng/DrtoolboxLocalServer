# Phase 3: Patient Engagement — Web Forms & Multi-Channel Communication - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-05-08  
**Phase:** 03-patient-engagement  
**Discussion Mode:** Auto-defaults (user deferred to Claude discretion)

---

## Scope Clarification

**User Decision:** Defer doctor-toolbox.com/chats integration to Phase 4+. Focus Phase 3 on:
1. Patient intake web form with HIS auto-population
2. Patient record dashboard (view for patients, edit for staff)
3. Unified staff inbox for LINE messages
4. Internal message routing (LINE ↔ patient records)

---

## Areas Discussed (Auto-Defaulted)

### Patient Intake Form & HIS Auto-Population

| Area | Decision |
|------|----------|
| **Form fields** | Core demographics + medical intake (name, phone, email, DOB, chief complaint, medications, allergies, appointment type) |
| **Validation** | Client-side UX feedback + server-side security. Phone/email format, DOB must be past date. |
| **Submission handling** | POST to `/api/patient/intake`. Idempotent via phone+email uniqueness. Duplicate returns existing patient_id. |
| **HIS population** | Direct INSERT to clinic.db. No approval workflow in Phase 3. |
| **Conflict resolution** | If phone+email exists, UPDATE existing record (merge). Log all updates for audit. |
| **Appointments** | Create pending appointment from form booking. Staff approves/schedules in dashboard. |

**Rationale:** Keep intake lean and extensible. Direct HIS insertion simplifies Phase 3; staff validation via dashboard provides quality gate.

---

### Patient Dashboard Design

| Area | Decision |
|------|----------|
| **Patient view** | Read-only: name, contact, medical summary, upcoming appointments, conversation history. Non-editable by patient. |
| **Staff view** | Full record access + edit capability. Searchable by name/phone/patient_id. |
| **Performance** | <1s load time. Cached patient record, lazy-load conversation history. Pagination for large lists. |
| **Caching strategy** | 5-minute cache for patient list. Manual refresh button for staff. |

**Rationale:** Staff needs editing capability; patients see their own data read-only. Caching balances performance vs. fresh HIS data.

---

### Staff Inbox for LINE Messages

| Area | Decision |
|------|----------|
| **Aggregation** | All patient LINE messages in one view. Default: unread-first, grouped by patient. |
| **Display** | Patient name, last message timestamp, unread count, escalation status. |
| **Context** | Click patient → 7-day conversation history from patient_conversations table. Staff can reply directly. |
| **Escalation handling** | Escalation-flagged messages show visual indicator (red badge). Include RAG confidence + original message context. |
| **Refresh strategy** | Polling every 3-5 seconds. Real-time WebSocket deferred to Phase 4+. |
| **Notifications** | Browser Notification API (if granted). Fallback: inbox badge count. |

**Rationale:** Simple polling avoids complexity in Phase 3. Real-time sync is Phase 4+ differentiator.

---

### Message Routing & Patient Matching

| Area | Decision |
|------|----------|
| **LINE ↔ Patient mapping** | line_user_id ↔ patient_id one-to-one mapping table. Created during intake or first LINE interaction. |
| **Form ↔ LINE matching** | No automatic matching (privacy concern). Staff manually links form submission to LINE user in dashboard. |
| **Fallback lookup** | If patient_id unknown, staff uses "Link LINE user" button to associate user_id with patient record. |
| **New LINE users** | When unknown LINE user messages, bot suggests completing intake form (with link). |

**Rationale:** Manual matching avoids false positives. Staff is curator of patient-LINE associations.

---

## Claude's Discretion (Not Locked)

These areas were defaulted by Claude and can be revisited during planning:
- **Field validation rules** (min/max lengths, regex patterns) — researcher will determine from clinic requirements
- **Dashboard UI layout** (single-page vs. multi-section) — planner/designer will refine based on wireframes
- **Polling interval tune** (3-5s starting point) — planner will adjust based on load testing
- **Staff role permissions** (which roles can edit) — clinic policy question

---

## Deferred (Not in Phase 3 Scope)

- doctor-toolbox.com/chats web chat interface
- Real-time WebSocket for staff inbox
- Multi-language support (Phase 3 = Traditional Chinese only)
- Advanced patient personalization (HIS context in RAG) — Phase 4+
- Voice-based intake — v2 requirement
- Patient self-service appointment booking

---

*Discussion completed: 2026-05-08*  
*Mode: Auto-defaults with scope clarification*  
*Next step: /gsd-plan-phase 3*
