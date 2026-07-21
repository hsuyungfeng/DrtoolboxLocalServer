# Phase 05: Clinical CRM & Advanced BI - Context

**Gathered:** 2026-07-21
**Status:** In Progress / Resumed
**Source:** Handoff State (.continue-here.md) & improveplan.md (Step 6)

<domain>
## Phase Boundary

This phase delivers the Clinical CRM, advanced BI insights (using ehrapy), and real-time medical staff alerts, as well as the optimization of patient engagement and medical answers localization. The scope includes:
- **Patient CRM Tracking & Analytics:** Real-time patient view in dashboard, ehrapy-based Leiden clustering for clinical grouping, and knowledge gap analysis from logs.
- **Staff Notifications & Alerts:** Real-time LINE/Email alerting when a patient mentions a "Red-flag" symptom.
- **RAG Medical Answers Optimization (Step 6):**
  - OTC drug name localization (e.g. mapping "乙醯胺酚" to "俗稱普拿疼的乙醯胺酚", "布洛芬" to "常見的布洛芬").
  - Clinic reservation CTA integration (e.g. injecting "點擊下方『預約門診』" links when high-risk symptoms or key clinical info is retrieved).
  - Active patient engagement questions at the end of medical responses (e.g. asking for pain location, character, duration, etc.).
- **Self-Healing & Monitor:** `HealthMonitorService` to automatically restart services and monitor resources.

</domain>

<decisions>
## Implementation Decisions

### Patient CRM & BI
- **Locked Decision:** Implement unified patient dashboard view at `/dashboard/staff/patient/<id>`.
- **Locked Decision:** Use `ehrapy` for clinical demographic analysis (age groups) and knowledge gap tracking.

### Alerting & Notifications
- **Locked Decision:** Detect red-flag symptoms in background threads and send real-time alerts to clinic staff via LINE/Email.

### Medical Localization & Interactive Engagement (Step 6)
- **Locked Decision:** In `src/rag_engine.py` (or prompt formatting), automatically format Acetaminophen and Ibuprofen to their localized names.
- **Locked Decision:** Integrate reservation CTA links prompting users to "點擊下方『預約門診』" when clinical conditions or red-flag warnings are triggered.
- **Locked Decision:** Append interactive follow-up questions inquiring about pain details (location, type, etc.) at the end of headache and general medical answers.

</decisions>

<canonical_refs>
## Canonical References

- `AGENTS.md` — Personas, strict pricing security rules, and language rules.
- `improveplan.md` — Step 6 (Medical Localization & Interactive Engagement).
- `src/rag_engine.py` — Core RAG response generator.
- `src/services/clinical_analyzer.py` — Analytical insights and knowledge gaps.
- `src/services/notification_service.py` — Alert notifications.
- `src/services/patient_service.py` — Patient CRM data.

</canonical_refs>
