# Roadmap

## Phase 1: Environment & PageIndex Core

**Goal:** Setup PageIndex, the local LLM reasoning engine, and the basic data segregation pipeline.

- Initialize PageIndex architecture.
- Integrate local Qwen (llama-qwen) via `llama.cpp`.
- Build the data ingestion pipeline (Clinic Special vs. General).

## Phase 2: Hermes Agent Orchestration & Logging

**Goal:** Route queries through Hermes and start logging interactions.

- Integrate `hermes-agent` for routing.
- Connect LINE/Web chat to the agent.
- Implement the JSON logging pipeline to `/data`.

## Phase 3: Web Dashboard & Feedback Loop

**Goal:** Give staff tools to curate the data.

- Build the Web Dashboard UI.
- Implement data viewer, editor, and exporter.
- Finalize the staff correction feedback loop.

### Phase 4: Integration of Medical Knowledge Graph

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 3
**Plans:** 1/1 plans complete

Plans:

- [x] TBD (run /gsd-plan-phase 4 to break down) (completed 2026-07-16)

## Phase 5: Clinical CRM & Advanced BI

**Goal:** Implement clinical CRM views, advanced analytics dashboards, and real-time staff alerts.

- Implement patient tracking view with LINE history and risk alerts.
- Build ehrapy-based clinical insights dashboard.
- Implement real-time notifications (LINE/Email) for high-risk patient symptoms.
- Optimize patient engagement questions, local OTC drug naming, and booking CTAs in RAG answers.

Plans:

- [ ] Define and execute Phase 5 prompts (run /gsd-plan-phase 5 to break down)

## Phase 6: OpenOutreach B2B Local Outreach & LINE Integration

**Goal:** Integrate OpenOutreach agentic email engine for local clinic B2B partnership outreach, bound with LINE VIP linking, strict pricing protection, and BI funnel tracking.

- Configure OpenOutreach Docker / Python agentic lead discovery for local business parks, clinics, and corporates (ICP 3-5km radius).
- Build bridge scripts connecting OpenOutreach outreach emails to DrtoolboxLocalServer LINE linking (`line_linking.py`).
- Enforce strict pricing security rules (AGENTS.md compliance) in LLM email copy generator.
- Integrate Corporate Outreach ROI dashboard (`tab-analytics` B2B funnel tracking).

Plans:

- [ ] Define and execute Phase 6 prompts (run /gsd-plan-phase 6 to break down)

