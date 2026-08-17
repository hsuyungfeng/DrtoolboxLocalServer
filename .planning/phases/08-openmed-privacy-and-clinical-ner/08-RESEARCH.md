# Phase 8: OpenMed Integration for Privacy & Clinical NER - Research

**Researched:** 2026-08-17
**Status:** Completed
**Domain:** Local Healthcare NLP, Clinical NER, PII De-identification, Graph-RAG, SOAP Processing

## Executive Summary

Integrating `openmed` provides DrtoolboxLocalServer with local-first, privacy-compliant NLP tools. The architecture operates entirely on-device (CPU/ONNX), avoiding competition for GPU VRAM with the local LLM (`Ornith-1.0-9B`). This research evaluates the integration patterns for:
1. PII/PHI De-identification across conversation logs and fine-tuning datasets (`verified_training_data.jsonl`).
2. Clinical Named Entity Recognition (NER) for query understanding in Graph-RAG and entity cross-validation in the SOAP note generation pipeline.

---

## 1. Technical Architecture & Component Analysis

### A. OpenMed SDK Architecture
- **Package**: `openmed` (Python 3.10+, PyTorch/ONNX runtime backends).
- **Core API**:
  - `openmed.extract_pii(text, model_name=..., lang='zh')`: Detects names, phone numbers, IDs, dates, addresses.
  - `openmed.deidentify(text, method='mask'|'replace'|'hash'|'shift_dates')`: Anonymizes text with Smart Merging to prevent token fragmentation.
  - `openmed.analyze_text(text, model_name=...)`: Extracts clinical entities with confidence scores and character spans.
- **Hardware Profile**:
  - Standard CPU execution / ONNX INT8 quantization utilizes ~100-300MB RAM, sub-50ms inference.
  - Leaves RTX 3060 and GTX 1060 GPUs 100% dedicated to Ornith-1.0-9B inference.

### B. DrtoolboxLocalServer Touchpoints

| Subsystem | File Path | Current State | OpenMed Enhancement |
| :--- | :--- | :--- | :--- |
| **Privacy / Log Sanitization** | `src/services/privacy_service.py` (New), `src/agent/hermes_core.py`, `data/verified_training_data.jsonl` | Raw text stored in JSONL logs | Automatically de-identify patient names, phones, IDs on write/export |
| **Graph-RAG Query Parsing** | `src/rag/clinical_ner.py` (New), `src/rag/graph_rag_engine.py` | String match / substring grep on `medical.db` | Clinical NER extracts `DISEASE` / `DRUG` / `SYMPTOM` entities for multi-hop graph retrieval |
| **SOAP Lab Generation** | `src/api/routes/dashboard.py`, `src/static/js/dashboard.js` | Direct LLM prompting on transcript | Clinical NER extracts structured prescriptions/conditions to cross-validate LLM SOAP output |

---

## 2. Risk & Mitigation Strategies

1. **Model Download & Offline Availability**:
   - *Risk*: First run may attempt downloading model weights from Hugging Face Hub if not cached.
   - *Mitigation*: Provide local fallback heuristics (regex-based PII masking + rule-based clinical term lookup from `clinic.db` & `medical.db`) so the system works even in completely air-gapped environments without network access.
2. **Performance Overhead**:
   - *Risk*: Synchronous NER calls might add latency to chat responses.
   - *Mitigation*: Run NER asynchronously or on lightweight ONNX CPU backend (<50ms per sentence).
3. **Language Compatibility**:
   - *Risk*: Traditional Chinese medical terminology variations.
   - *Mitigation*: Combine OpenMed's multilingual PII models (`lang='zh'`) with the existing Taiwan OTC drug mapping in `clinic.db` (`drugs.otc_name`).

---

## 3. Recommended Implementation Steps

- **Step 1**: Install and configure `openmed` dependency in `pyproject.toml` / `requirements.txt`.
- **Step 2**: Implement `src/services/privacy_service.py` with unit tests for PII masking/replacement.
- **Step 3**: Integrate PrivacyService into dataset curation and export endpoints in `src/api/routes/dashboard.py`.
- **Step 4**: Implement `src/rag/clinical_ner.py` and connect it into `src/rag/graph_rag_engine.py`.
- **Step 5**: Upgrade SOAP comparison endpoint (`/api/dashboard/soap/compare`) to extract and return clinical entity badges in the web UI.
- **Step 6**: Comprehensive pytest coverage in `tests/test_privacy_service.py` and `tests/test_clinical_ner.py`.
