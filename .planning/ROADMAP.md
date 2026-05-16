# Roadmap

## Phase 1: Environment & PageIndex Core
**Goal:** Setup PageIndex, the local LLM reasoning engine, and the basic data segregation pipeline.
- Initialize PageIndex architecture.
- Integrate local Gemma 4 27B via `llama.cpp`.
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
