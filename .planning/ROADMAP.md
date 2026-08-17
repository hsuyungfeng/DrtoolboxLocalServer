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

- [x] Define and execute Phase 6 prompts (run /gsd-plan-phase 6 to break down) (completed 2026-07-23)

## Phase 7: Multi-Channel 10km Local Business Scraping & Multi-Tier Outreach

**Goal:** Leverage Firecrawl deep-web scraping from `doctor-toolbox-post` to extract 10km local non-clinic business leads (FB, Messenger, Email, Posts), populate expanded `b2b_leads` database, and execute multi-channel outreach.

- Schema migration on `b2b_leads` (add `fb_page_url`, `fb_messenger_url`, `latest_post_url`, `category`, `outreach_channel`).
- Implement `scripts/local_b2b_scraper.py` using Firecrawl (`:3002`) to mine local businesses (gyms, yoga studios, tech firms, wedding photography) within 10km.
- Build Multi-Tier Outreach strategy: Email -> FB Messenger -> FB Post Comment.
- Update Web Dashboard `tab-analytics` B2B panel to visualize multi-channel conversion & LINE VIP linking.

Plans:

- [x] Define and execute Phase 7 prompts (completed 2026-07-23)

## Phase 8: OpenMed Integration for Privacy & Clinical NER

**Goal:** Integrate openmed local-first clinical NLP for HIPAA/GDPR PII de-identification in logs/datasets and clinical NER in Graph-RAG and SOAP pipelines.

- Build `PrivacyService` for automated PII masking, hashing, and synthetic replacement across conversation logs and training exports (`data/verified_training_data.jsonl`).
- Implement `ClinicalNER` wrapping openmed on CPU/ONNX to extract diseases, medications, and dosages.
- Integrate Clinical NER into `GraphRAGEngine` for enhanced clinical query resolution.
- Enhance SOAP Note comparison pipeline (`/api/dashboard/soap/compare`) with structured entity cross-validation and SOAP Lab UI tags.

Plans:

- [x] Define and execute Phase 8 prompts (08-01-PLAN.md) (completed 2026-08-17)

