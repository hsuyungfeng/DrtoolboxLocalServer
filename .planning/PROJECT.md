# [DrtoolboxLocalServer] Customer Service AI

## Context
**What this is:** A customer service AI and data collection platform built on a vectorless, reasoning-based RAG architecture (VectifyAI/PageIndex). It uses a local LLM (Gemma 4 27B via `llama.cpp`) for privacy-first reasoning and the Hermes Agent for orchestration. The primary focus is generating, reviewing, and collecting high-quality JSON QA pairs in the `/data` directory for future model fine-tuning, alongside a web dashboard for staff management.
**Why it matters:** It modernizes the clinic's local server environment, replacing legacy vector databases with a reasoning-first approach while strictly maintaining patient data privacy via local inference.
**Core Value:** Privacy-first, highly accurate customer service automation combined with a robust pipeline for collecting high-quality training data.

## Requirements

### Validated
- ✓ [Local Inference] — `llama.cpp` integration capable of serving local models (Gemma 4 27B).
- ✓ [Project Structure] — Existing Python/Flask structure with `/src`, `/data`, `/documents`, and Hermes agent orchestration components.

### Active
- [ ] Implement `PageIndex` vectorless reasoning RAG architecture (replacing Chroma/FAISS).
- [ ] Implement data-centric logging pipeline saving all interactions as JSON in `/data`.
- [ ] Build a Web Dashboard for clinic staff to view, edit, and export JSON training data.
- [ ] Create a feedback loop for staff to correct LLM answers and append them to the dataset.
- [ ] Integrate Hermes Agent to route LINE/Web chat queries to the PageIndex engine.

### Out of Scope
- [Cloud LLMs for Production] — All core inference must remain local for privacy.
- [Vector Databases] — Chroma/FAISS/clinic.db are explicitly deprecated in favor of PageIndex.

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Web Dashboard for UI | Staff need a visual interface to manage and correct QA logs easily. | — Pending |
| JSON format for Data | Standard and easy to parse format for downstream fine-tuning workflows. | — Pending |

## Evolution
This document evolves at phase transitions and milestone boundaries.

**After each phase transition** (via `/gsd-transition`):
1. Requirements invalidated? → Move to Out of Scope with reason
2. Requirements validated? → Move to Validated with phase reference
3. New requirements emerged? → Add to Active
4. Decisions to log? → Add to Key Decisions
5. "What This Is" still accurate? → Update if drifted

**After each milestone** (via `/gsd-complete-milestone`):
1. Full review of all sections
2. Core Value check — still the right priority?
3. Audit Out of Scope — reasons still valid?
4. Update Context with current state

---
*Last updated: 2026-05-16 after initialization*
