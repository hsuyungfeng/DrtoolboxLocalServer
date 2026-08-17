# Phase 8: OpenMed Integration for Privacy & Clinical NER - Context

**Gathered:** 2026-08-17
**Status:** Ready for planning
**Source:** User Request & OpenMed Architecture Deep Research

<domain>
## Phase Boundary

This phase integrates `openmed` (Apache-2.0 Local-First Healthcare NLP) into DrtoolboxLocalServer to provide:
1. **Stage 1 (Privacy & PII De-identification)**: 100% on-device PII/PHI extraction and anonymization (Masking/Hashing/Faker Replacement) across chat logs, audio transcription storage, and training dataset exports (`data/verified_training_data.jsonl`).
2. **Stage 2 (Clinical NER & SOAP Verification)**: Local-first clinical named entity recognition (Diseases, Medications, Dosages, Symptoms) integrated into Graph-RAG query resolution (`src/rag/graph_rag_engine.py`) and the SOAP note generation/validation pipeline (`src/api/routes/dashboard.py`).

</domain>

<decisions>
## Implementation Decisions

### 1. Stage 1: Privacy Service & Training Data De-identification (`src/services/privacy_service.py`)
- Wrap `openmed.deidentify` and `openmed.extract_pii` into a unified `PrivacyService`.
- Support configurable anonymization policies (`mask`, `replace`, `hash`, `shift_dates`).
- Hook into `data/verified_training_data.jsonl` export and live conversation logging in `src/agent/hermes_core.py` and `src/api/routes/dashboard.py`.
- Ensure zero patient identity leaks in exported files or fine-tuning datasets.

### 2. Stage 2: Clinical Entity Extractor (`src/rag/clinical_ner.py`)
- Implement a CPU/ONNX friendly clinical NER wrapper using `openmed` disease and pharma models (`disease_detection_superclinical`, `pharma_detection_superclinical`).
- Include fallback heuristic extractors when offline/cold to guarantee non-blocking operations.

### 3. Graph-RAG Entity Resolution Enhancement (`src/rag/graph_rag_engine.py`)
- Enhance `query_integrated` and `search_entities` to utilize `ClinicalNER` output for multi-hop relationship retrieval in `data/db/medical.db` (8,800+ diseases & drugs).
- Map extracted drug names to `otc_name` in `clinic.db` dynamically.

### 4. SOAP Lab Validation Pipeline (`src/api/routes/dashboard.py` & `src/static/js/dashboard.js`)
- In `POST /api/dashboard/soap/compare` and `POST /api/dashboard/soap/intercept`:
  - Run `ClinicalNER` on transcript text to extract structured entities (`DISEASE`, `DRUG`, `DOSAGE`, `SYMPTOM`).
  - Cross-validate against LLM generated Assessment (A) and Plan (P).
  - Return extracted clinical entities to the frontend SOAP Lab interface with visual badges.

</decisions>

<canonical_refs>
## Canonical References

- `https://github.com/maziyarpanahi/openmed` — OpenMed Python SDK & Model Registry
- `src/rag/graph_rag_engine.py` — SQLite Graph-RAG Engine
- `src/api/routes/dashboard.py` — SOAP comparison and log curation endpoints
- `data/verified_training_data.jsonl` — Golden training dataset
- `AGENTS.md` — Pricing and privacy protection regulations

</canonical_refs>

<specifics>
## Specific Ideas

- Run OpenMed purely on CPU or low-memory ONNX mode so GPU VRAM remains dedicated to Ornith-1.0-9B on GTX 1060 / RTX 3060.
- Provide Pytest unit tests for both PII masking and Clinical NER extraction.

</specifics>

<deferred>
## Deferred Ideas

- FHIR / HL7 v2 bundle export (can be evaluated in a later phase for hospital EMR integration).

</deferred>

---

*Phase: 08-openmed-privacy-and-clinical-ner*
*Context gathered: 2026-08-17*
