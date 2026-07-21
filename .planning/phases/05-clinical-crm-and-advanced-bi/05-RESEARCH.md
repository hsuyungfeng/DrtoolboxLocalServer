# Phase 05: Clinical CRM & Advanced BI - Research

This document outlines the technical research for implementing clinical CRM notifications, local OTC drug naming, and booking integration in `DrtoolboxLocalServer`.

---

## 1. OTC Drug Localization Strategy
In Taiwan, patients are highly familiar with brand names like "普拿疼" (Acetaminophen) or "EVE" (Ibuprofen) rather than their chemical/generic names.
- When generating answers regarding common painkillers, we will intercept the prompt formatting in `src/rag_engine.py` or pre-process RAG source chunks to rewrite:
  - `乙醯胺酚` -> `俗稱普拿疼的乙醯胺酚`
  - `布洛芬` -> `常見的布洛芬`
- This ensures patients easily recognize the medication while maintaining academic correctness.

---

## 2. Booking CTA & Red-flag Warnings Integration
- **CTA Prompt:**
  `若您有上述紅旗症狀，或是頭痛已影響日常，建議您點擊下方『預約門診』由我們的專科醫師為您評估，以利安排進一步檢查。`
- **Trigger Condition:**
  1. Detect critical red-flag keywords in the user question (e.g., `發燒`, `劇痛`, `流血`, `雷擊`).
  2. Detect general headache/medical symptoms queries in `hermes_router.py` (which routes to `general` category).
- **Implementation:**
  Append the reservation instructions to the system instructions within `src/rag_engine.py` when matching these triggers, instructing the LLM to include the booking link/warning at the appropriate place or end of the text.

---

## 3. Patient Engagement & Follow-up Questions
To collect structured symptoms prior to physician visits, the bot should prompt for details:
- **Questions:**
  `若您能補充頭痛的部位、性質（如搏動/緊箍/刺痛）、持續時間、誘發因素或已嘗試的緩解方式，我可為您提供更精準的建議！`
- **Implementation:**
  Modify system instruction prompt templates in `src/rag_engine.py` (general route and special route) to explicitly mandate ending medical consultation answers with these interactive triage questions.

---

## 4. Verification Plan
- **Mock Tests:** Verify formatting filters in `tests/test_high_risk_notify.py` or a dedicated test suite.
- **RAG Integration Test:** Query the API and assert the exact localized phrases and CTAs appear in the response payload.
