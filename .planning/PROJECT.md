# DrtoolboxLocalServer — Local Clinic Intelligence Platform

## What This Is

**DrtoolboxLocalServer** is a self-contained clinic intelligence platform that integrates medical data analysis, patient communication, and AI-powered consultation through a local RAG system. It bridges local HIS (Hospital Information System) databases with cloud integrations (doctor-toolbox.com) and provides multi-channel patient engagement via LINE.

### Core Value

Enable clinic staff and patients to access intelligent medical decision support and seamless communication without dependency on external cloud systems, while maintaining data privacy through local-first architecture.

## Vision

A unified clinic platform that:
- **Understands patient queries** using RAG (Retrieval-Augmented Generation) against medical documents
- **Analyzes clinic data** locally on on-premises HIS systems with optional cloud sync
- **Enables patient communication** through LINE and doctor-toolbox.com/chats interfaces
- **Powers edge AI** using local LLMs (Qwen 3.6, Gemma 4) on available GPU (2080Ti, 22GB VRAM)
- **Grows intelligently** with Hermes agent auto-skills and CLI tools that adapt to clinic needs

## Context

- **Organization**: Clinic (healthcare provider)
- **Users**: Clinic staff, patients, medical professionals
- **Deployment**: On-premises local server + optional cloud sync
- **Technology Constraints**: 2080Ti GPU (22GB VRAM), llama.cpp for local LLM inference

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| **Local-first LLM inference** | Privacy, offline operation, no API keys per query | llama.cpp + Qwen/Gemma on 2080Ti |
| **Hermes agent for growth** | Auto-skills learn from clinic patterns, CLI tools adapt | Agent expands with clinic needs |
| **Multi-channel communication** | Patients use preferred platform; staff manage from one place | LINE + doctor-toolbox.com/chats integration |
| **HIS + Cloud sync** | Local analysis for speed/privacy; cloud for backup/advanced analytics | Bidirectional sync with doctor-toolbox.com |
| **Federated RAG (Dual KB)** | Separate general medical vs clinic operational data | Intent Router directs query to `general_medical` or `clinic_specific` to prevent hallucination |

## Requirements

### Validated (Completed in Phase 1, 2, 3)

**RAG Medical Chatbot (Federated RAG)**
- [x] Ingest clinic medical documents (PDF, Word, text files) into `general_medical`
- [x] Index operational documents into `clinic_specific` using OCR scripts
- [x] Answer patient queries using Dual RAG pipeline with Intent Classification
- [x] Provide confidence scores and source citations

**HIS & Web Integration**
- [x] Connect to local HIS database (Read-Only access)
- [x] Execute analytical queries on patient/clinic data
- [x] Patient intake web form and Patient record dashboard (Read-only UI)
- [x] Conflict resolution endpoint

**Patient Communication**
- [x] LINE bot integration for patient queries
- [x] Unified message queue (staff interface with CRUD)
- [x] Conversation history and context retention

### Active

**Hermes Agent & Auto-Skills**
- [ ] Connect Hermes Agent to local HIS database
- [ ] Auto-skill discovery: learn from clinic data patterns
- [ ] Cloud sync: bidirectional data flow with doctor-toolbox.com
- [ ] CRM features: patient record management

**Local LLM Infrastructure**
- [ ] Support voice input/output (future phase)
- [ ] llama.cpp setup and optimization for 2080Ti (Ongoing)
- [ ] Model management (Qwen 3.6, Gemma 4 support)
- [ ] Inference serving (API endpoint for RAG and agent)
- [ ] Performance monitoring and resource management

**CLI & Auto-Skills**
- [ ] Hermes CLI with clinic-specific commands
- [ ] Auto-skill creation from successful agent patterns
- [ ] Skill discovery and loading
- [ ] Growth metrics (skill adoption, usage patterns)

### Out of Scope

- [ ] Multi-clinic federation (single clinic per server)
- [ ] Real-time video consultation (use external tools)
- [ ] Advanced medical image analysis (future post-MVP)
- [ ] HIPAA/GDPR compliance validation (clinic responsibility, design supports it)

## Success Metrics

1. **RAG Chatbot**: Patients receive answers to medical queries within 3 seconds, with 80%+ relevance rating
2. **Hermes Analysis**: Clinic staff run ad-hoc queries on 100K+ patient records in <5s
3. **Communication**: 90%+ patient questions answered through LINE without human escalation
4. **LLM Efficiency**: Model inference constrained to 2080Ti without memory overflow (streaming output)
5. **Growth**: Clinic defines 5+ custom skills within first month of operation

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

*Last updated: 2026-05-06 after initialization*
