# Phase 05: Clinical CRM & Advanced BI - Plan

- **Phase:** 05
- **Name:** Clinical CRM & Advanced BI
- **Goal:** Build the clinical CRM tracking, ehrapy BI analytics, real-time staff alerts, and optimize local medical answers and patient engagement.

---

## 1. Threat Model
- **Threat 1: False Positive/Negative Red-flags.** High-risk symptoms are missed or generate too many alerts.
  - *Mitigation:* Use strict keyword lists combined with clinical classification triggers, allowing staff to customize sensitivity.
- **Threat 2: Privacy Leakage in Notifications.** LINE notifications to staff contain full unredacted patient data over public networks.
  - *Mitigation:* Only send notification alerts containing patient mapping ID and symptom categories; do not include full chat history or real names unless encrypted.

---

## 2. Tasks

### Milestone 1: CRM & BI Insights (Completed/Polished)
- [x] **Task 1.1: Build Patient Detail View**
  - Implement `/dashboard/staff/patient/<id>` aggregating HIS history, LINE history, and symptom risk rating.
- [x] **Task 1.2: ehrapy Dashboard Integration**
  - Add age distribution graphs and AI "Knowledge Gaps" metrics to the Analytics tab.

### Milestone 2: Real-time Staff Alerting
- [ ] **Task 2.1: Implement High-risk Symptom Notification**
  - Update `src/services/notification_service.py` to trigger LINE Push / Email alerts when red-flags are detected in chat logs.
- [ ] **Task 2.2: Add Risk Alerting Background Thread**
  - Run background thread checking incoming queries for critical terms (流血, 劇痛, 發燒, 呼吸困難) and log risk status.

### Milestone 3: Localization & Interactive Engagement (Step 6)
- [ ] **Task 3.1: OTC Drug Localization**
  - Modify `src/rag_engine.py` (specifically in `query_integrated`) to search for generic names ("乙醯胺酚", "布洛芬") in LLM-bound prompts/outputs, translating or appending localized common names:
    - `乙醯胺酚` -> `俗稱普拿疼的乙醯胺酚`
    - `布洛芬` -> `常見的布洛芬`
- [ ] **Task 3.2: Reservation CTA Integration**
  - Append booking warnings and CTA prompts (例如：「若您有上述紅旗症狀，或是頭痛已影響日常，建議您**點擊下方『預約門診』**由我們的專科醫師為您評估，以利安排進一步檢查。」) when matching queries or warning thresholds.
- [ ] **Task 3.3: Patient Engagement Follow-up Questions**
  - Format the final system prompt or answer template to append interactive medical follow-up questions at the end (e.g. asking for pain location, character, duration, etc.) for headache and other core medical topics.

### Milestone 4: Verification & Data Expansion
- [ ] **Task 4.1: Populate clinic.db with Diverse Simulated Patients**
  - Write or run data expansion script to add 100+ diverse simulated patients with varied visits to test Leiden clustering.
- [ ] **Task 4.2: E2E Verification Tests**
  - Add pytest test cases verifying the localization formatting, CTA injection, and follow-up prompts in final responses.

---

## 3. Definition of Done
- CRM dashboard renders Leiden clustering and knowledge gaps successfully.
- High-risk symptoms trigger staff alerts in less than 2 seconds.
- Final medical responses automatically localize OTC drug terms and display interactive patient engagement questions and reservation CTAs.
