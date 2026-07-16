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
