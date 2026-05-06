# DrtoolboxLocalServer — Execution Roadmap

## Phase Structure

Five coarse-grained phases deliver value incrementally while building toward full clinic intelligence platform.

---

## Phase 1: Foundation — Local LLM & RAG Infrastructure

**Objective**: Establish local LLM inference and core RAG pipeline for medical document Q&A.

**Requirements**:
- LLM-01: Install and configure llama.cpp on 2080Ti GPU
- LLM-02: Load and serve Qwen 3.6 model with inference API
- LLM-03: Optimize inference for 22GB VRAM constraint
- LLM-04: Monitor GPU memory and prevent overflow conditions
- RAG-01: Ingest and index clinic medical documents (PDF, Word, text)
- RAG-02: Parse structured medical text for semantic search
- RAG-03: Answer patient queries against indexed documents with confidence scores
- RAG-04: Provide source citations and document references in responses

**Outcomes**:
- ✓ llama.cpp running on GPU with stable inference
- ✓ Qwen 3.6 model serving at <200ms latency
- ✓ RAG pipeline ingesting and searching medical documents
- ✓ Confidence scores and citations in all responses

**Success Criteria**:
1. Model loads without OOM, achieves target latency
2. Medical document index queryable with >0.7 relevance
3. RAG responses include source document references
4. No GPU memory leaks over 24h operation

**Deliverables**:
- llama.cpp setup guide and config
- RAG ingestion and indexing pipeline
- Inference API server
- Documentation for clinic staff

**Plans:**
- [x] 01-foundation/01-PLAN.md — Foundation: LLM + RAG Infrastructure - COMPLETED
- [ ] 02-LLM 優化與測試 — TODO
- [ ] 03-RAG 搜尋優化 — TODO
- [ ] 04-API 完整化 — TODO

**Estimated Effort**: 2-3 weeks

---

## Phase 2: Clinic Integration — HIS Database & LINE Communication

**Objective**: Connect to clinic HIS database and enable patient communication via LINE.

**Requirements**:
- DB-01: Connect to local HIS database (read-only queries)
- DB-02: Execute analytical queries on patient/clinic data
- DB-03: Cache query results for performance
- COMM-01: Integrate LINE bot for patient inquiries
- COMM-02: Route messages to RAG chatbot and store responses
- COMM-03: Maintain conversation history per patient

**Outcomes**:
- ✓ HIS database accessible for analytical queries
- ✓ LINE bot receives and responds to patient messages
- ✓ Conversation history persisted per patient
- ✓ Query results cached for performance

**Success Criteria**:
1. HIS read-only connection stable with no data leaks
2. Line bot responds to 100% of incoming messages within 5s
3. Query results cached; repeat queries <100ms
4. Conversation history accurate and retrievable

**Deliverables**:
- HIS database connection module
- LINE bot integration and message routing
- Conversation history storage and retrieval
- Performance monitoring for queries

**Estimated Effort**: 2-3 weeks

---

## Phase 3: Patient Engagement — Web Forms & Multi-Channel Communication

**Objective**: Provide web-based patient intake and unified staff communication interface.

**Requirements**:
- WEB-01: Create patient intake web form
- WEB-02: Auto-populate HIS database from form submissions
- WEB-03: Display patient record dashboard
- COMM-04: Integrate doctor-toolbox.com/chats for web-based patient chat
- COMM-05: Unified inbox for staff (manage LINE + web chat in one interface)

**Outcomes**:
- ✓ Web form collects patient intake data securely
- ✓ Form submissions auto-populate HIS database
- ✓ Patient dashboard displays current records
- ✓ Staff can manage all patient communication in one interface

**Success Criteria**:
1. Form submissions persist to HIS without data loss
2. Staff inbox aggregates LINE and web chat messages
3. Patient dashboard loads in <2s
4. Message routing accurate across all channels

**Deliverables**:
- Patient intake web form
- Auto-population integration
- Patient record dashboard
- Unified staff inbox UI
- doctor-toolbox.com/chats integration

**Estimated Effort**: 2-3 weeks

---

## Phase 4: Intelligence Growth — Hermes Agent & Auto-Skills

**Objective**: Deploy Hermes agent for pattern learning and enable auto-skill generation.

**Requirements**:
- AGENT-01: Spawn Hermes agent instance with local HIS context
- AGENT-02: Agent learns clinic-specific patterns from queries
- AGENT-03: Agent exposes custom CLI commands for clinic staff
- SKILL-01: Auto-skill creation from successful agent patterns
- SKILL-02: Skill discovery and dynamic loading
- SKILL-03: Skill adoption metrics and growth reporting

**Outcomes**:
- ✓ Hermes agent initialized with clinic data context
- ✓ Agent identifies and learns clinic-specific query patterns
- ✓ Custom CLI commands generated from agent patterns
- ✓ Auto-skills dynamically loaded and tracked

**Success Criteria**:
1. Agent initializes with HIS context without errors
2. 5+ custom skills created within first 2 weeks of operation
3. Clinic staff can invoke auto-generated commands
4. Skill adoption metrics tracked and reported

**Deliverables**:
- Hermes agent initialization and context setup
- Pattern learning system
- Auto-skill generator
- CLI command registration
- Metrics dashboard for skill adoption

**Estimated Effort**: 2-3 weeks

---

## Phase 5: Enterprise Features — Cloud Sync & Optimization

**Objective**: Enable cloud backup/analytics and optimize all systems for production stability.

**Requirements**:
- SYNC-01: Bidirectional sync of patient data with doctor-toolbox.com
- SYNC-02: Sync clinic analytics and insights to cloud dashboard

**Outcomes**:
- ✓ Patient data syncs bidirectionally to cloud
- ✓ Clinic analytics visible in doctor-toolbox.com dashboard
- ✓ All systems operating at production scale
- ✓ All v1 success metrics achieved

**Success Criteria**:
1. Data sync latency <5min, zero loss
2. Cloud dashboard reflects real-time clinic data
3. RAG response time <3s (success metric achieved)
4. Hermes queries <5s on 100K+ records (success metric achieved)
5. 90%+ auto-answered patient questions (success metric achieved)

**Deliverables**:
- Cloud sync integration (doctor-toolbox.com API)
- Analytics dashboard
- Production hardening and monitoring
- Performance tuning and optimization

**Estimated Effort**: 2-3 weeks

---

## Requirement Traceability

| Requirement | Phase | Category | Status |
|-------------|-------|----------|--------|
| LLM-01 | 1 | Local LLM | Table Stakes |
| LLM-02 | 1 | Local LLM | Table Stakes |
| LLM-03 | 1 | Local LLM | Table Stakes |
| LLM-04 | 1 | Local LLM | Table Stakes |
| RAG-01 | 1 | Medical AI | Table Stakes |
| RAG-02 | 1 | Medical AI | Table Stakes |
| RAG-03 | 1 | Medical AI | Table Stakes |
| RAG-04 | 1 | Medical AI | Table Stakes |
| DB-01 | 2 | Clinic Data | Table Stakes |
| DB-02 | 2 | Clinic Data | Table Stakes |
| DB-03 | 2 | Clinic Data | Table Stakes |
| COMM-01 | 2 | Communication | Table Stakes |
| COMM-02 | 2 | Communication | Table Stakes |
| COMM-03 | 2 | Communication | Table Stakes |
| WEB-01 | 3 | Patient Engagement | Table Stakes |
| WEB-02 | 3 | Patient Engagement | Table Stakes |
| WEB-03 | 3 | Patient Engagement | Table Stakes |
| AGENT-01 | 4 | Hermes Intelligence | Differentiator |
| AGENT-02 | 4 | Hermes Intelligence | Differentiator |
| AGENT-03 | 4 | Hermes Intelligence | Differentiator |
| COMM-04 | 3 | Communication | Differentiator |
| COMM-05 | 3 | Communication | Differentiator |
| SKILL-01 | 4 | Auto-Skills | Differentiator |
| SKILL-02 | 4 | Auto-Skills | Differentiator |
| SKILL-03 | 4 | Auto-Skills | Differentiator |
| SYNC-01 | 5 | Cloud Sync | Differentiator |
| SYNC-02 | 5 | Cloud Sync | Differentiator |

**Coverage**: 100% of v1 requirements mapped to phases

---

## Timeline

- **Phase 1** (Weeks 1-3): Foundation
- **Phase 2** (Weeks 4-6): Clinic Integration
- **Phase 3** (Weeks 7-9): Patient Engagement
- **Phase 4** (Weeks 10-12): Intelligence Growth
- **Phase 5** (Weeks 13-15): Enterprise Features

**Total Estimated Timeline**: 15 weeks to production readiness

---

## Success Metrics Alignment

Each phase contributes to the overarching success metrics:

| Metric | Phases | Target |
|--------|--------|--------|
| RAG response time | 1, 5 | <3 seconds, 80%+ relevance |
| HIS query latency | 2, 5 | <5 seconds on 100K+ records |
| Auto-answered questions | 2, 3, 4, 5 | 90%+ without human escalation |
| GPU efficiency | 1, 5 | No overflow, streaming output |
| Auto-skills | 4, 5 | 5+ custom skills in Month 1 |

---

## Risk & Mitigation

| Risk | Mitigation | Phase |
|------|-----------|-------|
| GPU memory overflow under load | Early performance testing in Phase 1, streaming fallback | 1 |
| HIS connectivity fragility | Comprehensive error handling, fallback to cached queries | 2 |
| Message routing failures | Redundancy, message queuing, idempotency | 2, 3 |
| Slow skill learning curve | Early pattern discovery, manual pattern seeds | 4 |
| Cloud sync data conflicts | Conflict resolution strategy, audit trail | 5 |

---

## Decision Gate: Phase Entry Requirements

Before entering a phase:
1. ✓ Previous phase success criteria met or waived
2. ✓ All blocking requirements from prior phases complete
3. ✓ No critical incidents or blockers from prior phase
4. ✓ Team readiness confirmed

---

*Last updated: 2026-05-06 after roadmap creation*
