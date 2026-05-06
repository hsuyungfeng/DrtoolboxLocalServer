# DrtoolboxLocalServer — v1 Requirements

## v1 Requirements

### Table Stakes — Medical AI & Clinic Operations

**Core Medical Intelligence (Must Have)**
- [ ] **RAG-01** — Ingest and index clinic medical documents (PDF, Word, text)
- [ ] **RAG-02** — Parse structured medical text for semantic search
- [ ] **RAG-03** — Answer patient queries against indexed documents with confidence scores
- [ ] **RAG-04** — Provide source citations and document references in responses

**Local LLM Infrastructure (Must Have)**
- [ ] **LLM-01** — Install and configure llama.cpp on 2080Ti GPU
- [ ] **LLM-02** — Load and serve Qwen 3.6 model with inference API
- [ ] **LLM-03** — Optimize inference for 22GB VRAM constraint
- [ ] **LLM-04** — Monitor GPU memory and prevent overflow conditions

**Clinic Database Integration (Must Have)**
- [ ] **DB-01** — Connect to local HIS database (read-only queries)
- [ ] **DB-02** — Execute analytical queries on patient/clinic data
- [ ] **DB-03** — Cache query results for performance

**Patient Communication Gateway (Must Have)**
- [ ] **COMM-01** — Integrate LINE bot for patient inquiries
- [ ] **COMM-02** — Route messages to RAG chatbot and store responses
- [ ] **COMM-03** — Maintain conversation history per patient

**Web Interface & CRM (Table Stakes)**
- [ ] **WEB-01** — Create patient intake web form
- [ ] **WEB-02** — Auto-populate HIS database from form submissions
- [ ] **WEB-03** — Display patient record dashboard

---

### Differentiators — Hermes Growth & Cloud Integration

**Hermes Agent for Analysis (Differentiator)**
- [ ] **AGENT-01** — Spawn Hermes agent instance with local HIS context
- [ ] **AGENT-02** — Agent learns clinic-specific patterns from queries
- [ ] **AGENT-03** — Agent exposes custom CLI commands for clinic staff

**Cloud Sync (Differentiator)**
- [ ] **SYNC-01** — Bidirectional sync of patient data with doctor-toolbox.com
- [ ] **SYNC-02** — Sync clinic analytics and insights to cloud dashboard

**Auto-Skills (Differentiator)**
- [ ] **SKILL-01** — Auto-skill creation from successful agent patterns
- [ ] **SKILL-02** — Skill discovery and dynamic loading
- [ ] **SKILL-03** — Skill adoption metrics and growth reporting

**Multi-Channel Communication (Differentiator)**
- [ ] **COMM-04** — Integrate doctor-toolbox.com/chats for web-based patient chat
- [ ] **COMM-05** — Unified inbox for staff (manage LINE + web chat in one interface)

---

## v2 Requirements (Deferred)

- Voice input/output for RAG chatbot (speech-to-text, text-to-speech)
- Gemma 4 model support and multi-model selection
- Advanced analytics dashboard for clinic operations
- Real-time patient monitoring and alerts
- Integration with electronic prescribing systems
- Doctor-toolbox.com CRM full-feature sync

---

## Out of Scope

- **Multi-clinic federation** — Single clinic per server instance
- **Video consultation** — Use existing platforms (Google Meet, Zoom); we provide chat/messaging
- **Medical image analysis** — Deferred to v2; focus on textual medical knowledge
- **HIPAA/GDPR compliance validation** — Clinic responsible; design supports secure practices
- **Mobile app** — Web app responsive to mobile; native app in v2

---

## Traceability

| Requirement | Phase | Category | Type | Status |
|-------------|-------|----------|------|--------|
| RAG-01 | 1 | Medical AI | Table Stakes | Pending |
| RAG-02 | 1 | Medical AI | Table Stakes | Pending |
| RAG-03 | 1 | Medical AI | Table Stakes | Pending |
| RAG-04 | 1 | Medical AI | Table Stakes | Pending |
| LLM-01 | 1 | Local LLM | Table Stakes | Pending |
| LLM-02 | 1 | Local LLM | Table Stakes | Pending |
| LLM-03 | 1 | Local LLM | Table Stakes | Pending |
| LLM-04 | 1 | Local LLM | Table Stakes | Pending |
| DB-01 | 2 | Clinic Data | Table Stakes | Pending |
| DB-02 | 2 | Clinic Data | Table Stakes | Pending |
| DB-03 | 2 | Clinic Data | Table Stakes | Pending |
| COMM-01 | 2 | Communication | Table Stakes | Pending |
| COMM-02 | 2 | Communication | Table Stakes | Pending |
| COMM-03 | 2 | Communication | Table Stakes | Pending |
| WEB-01 | 3 | Patient Engagement | Table Stakes | Pending |
| WEB-02 | 3 | Patient Engagement | Table Stakes | Pending |
| WEB-03 | 3 | Patient Engagement | Table Stakes | Pending |
| AGENT-01 | 4 | Hermes Intelligence | Differentiator | Pending |
| AGENT-02 | 4 | Hermes Intelligence | Differentiator | Pending |
| AGENT-03 | 4 | Hermes Intelligence | Differentiator | Pending |
| COMM-04 | 3 | Communication | Differentiator | Pending |
| COMM-05 | 3 | Communication | Differentiator | Pending |
| SKILL-01 | 4 | Auto-Skills | Differentiator | Pending |
| SKILL-02 | 4 | Auto-Skills | Differentiator | Pending |
| SKILL-03 | 4 | Auto-Skills | Differentiator | Pending |
| SYNC-01 | 5 | Cloud Sync | Differentiator | Pending |
| SYNC-02 | 5 | Cloud Sync | Differentiator | Pending |

**Coverage**: 100% of v1 requirements mapped to execution phases

---

## Quality Criteria

All v1 requirements are:
- ✓ **Specific and testable**: "User can X" with observable outcome
- ✓ **User-centric**: Focused on clinic staff or patient capability
- ✓ **Atomic**: One capability per requirement
- ✓ **Independent**: Minimal cross-requirement dependencies

---

*Last updated: 2026-05-06 after requirements definition*
