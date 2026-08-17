# Phase 8 Plan 1: OpenMed Integration for Privacy De-identification & Clinical NER

## Overview
Integrate `openmed` into DrtoolboxLocalServer to provide local-first, on-device PII/PHI de-identification across log files/training exports and empower Graph-RAG / SOAP note pipelines with lightweight Clinical Named Entity Recognition (NER).

---

## Execution Tasks

### Task 1: Environment & Dependency Setup
- Add `openmed` to dependencies (e.g. `pyproject.toml` / `requirements.txt`).
- Establish CPU/ONNX configuration profile to ensure zero GPU VRAM impact on Ornith-1.0-9B.
- **Files Modified**: `pyproject.toml`

### Task 2: Privacy Service Implementation (`src/services/privacy_service.py`)
- Implement `PrivacyService` class supporting:
  - `anonymize_text(text, method='mask', lang='zh')`: Mask/replace patient names, phone numbers, IDs, and addresses.
  - `anonymize_conversation(messages)`: Batch anonymize chat turn JSON structures.
  - Offline fallback regex handlers when OpenMed model weights are loading or offline.
- **Files Created**: `src/services/privacy_service.py`

### Task 3: Training Data & Log Export De-identification Pipeline
- Update `src/api/routes/dashboard.py` and `src/agent/hermes_core.py` to route training data exports through `PrivacyService.anonymize_conversation` before writing to `data/verified_training_data.jsonl` or CSV/JSON downloads.
- Add endpoint `POST /api/dashboard/privacy/deidentify` for staff batch de-identification preview in the Curation dashboard.
- **Files Modified**: `src/api/routes/dashboard.py`, `src/agent/hermes_core.py`

### Task 4: Clinical NER Service (`src/rag/clinical_ner.py`)
- Implement `ClinicalNER` class wrapping OpenMed clinical models (`disease_detection_superclinical`, `pharma_detection_superclinical`):
  - `extract_entities(text)`: Returns structured list of `[{'text': str, 'label': 'DISEASE'|'DRUG'|'DOSAGE'|'SYMPTOM', 'confidence': float, 'start': int, 'end': int}]`.
  - Fallback mechanism utilizing `clinic.db` (`drugs` table) and `medical.db` terms.
- **Files Created**: `src/rag/clinical_ner.py`

### Task 5: Graph-RAG Entity Resolution Enhancement (`src/rag/graph_rag_engine.py`)
- Integrate `ClinicalNER` in `GraphRAGEngine.query_integrated()` and `GraphRAGEngine.search_entities()`.
- Use extracted entities to prioritize 1-hop and 2-hop clinical relationship traversals.
- **Files Modified**: `src/rag/graph_rag_engine.py`

### Task 6: SOAP Note Generation & Cross-Validation Pipeline (`dashboard.py` & `dashboard.js`)
- In `POST /api/dashboard/soap/compare` and `POST /api/dashboard/soap/intercept`:
  - Run `ClinicalNER` over patient audio transcript text.
  - Return extracted clinical entities along with the LLM generated SOAP result.
  - Update `dashboard.js` and `dashboard.html` SOAP Lab to display clinical entity tags (Drugs, Dosages, Diagnoses) next to the SOAP note comparison.
- **Files Modified**: `src/api/routes/dashboard.py`, `src/static/js/dashboard.js`, `src/templates/dashboard.html`

### Task 7: Unit Testing & Verification
- Implement comprehensive unit tests:
  - `tests/test_privacy_service.py`: Verify PII masking, replacement, and JSONL log sanitization.
  - `tests/test_clinical_ner.py`: Verify entity extraction on clinical transcripts and Graph-RAG integration.
- Run `uv run pytest tests/test_privacy_service.py tests/test_clinical_ner.py`.
- **Files Created**: `tests/test_privacy_service.py`, `tests/test_clinical_ner.py`

---

## Verification Criteria
1. `PrivacyService.anonymize_text` successfully redacts patient names and phone numbers without corrupting text flow.
2. `ClinicalNER.extract_entities` returns typed entities (`DRUG`, `DISEASE`, `DOSAGE`) in under 100ms on CPU.
3. SOAP comparison endpoint returns `extracted_entities` metadata and renders correctly in SOAP Lab UI.
4. All Pytest test suites pass cleanly.
