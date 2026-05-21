# Phase 1: Environment & PageIndex Core - Plan

## 1. Setup Local LLM Inference
- **Description:** Configure `llama-qwen` (llama.cpp) to run Qwen and expose it via an API or python binding for PageIndex.
- **Files Modified:** `src/llm_server.py`, `requirements.txt`
- **Dependencies:** None
- **Acceptance Criteria:** A local request to the LLM returns a valid reasoning response.

## 2. Initialize PageIndex Architecture
- **Description:** Create the PageIndex client and wrapper classes to interface with the local LLM.
- **Files Modified:** `src/rag_engine.py`, `config/settings.py`
- **Dependencies:** 1
- **Acceptance Criteria:** PageIndex can successfully build a small test tree and query it using the local LLM.

## 3. Data Segregation Pipeline
- **Description:** Implement a data loader that reads from `/media/hsu/软件/行銷圖文檔案整理` for Clinic Special Data, and separate logic for General Medical Data.
- **Files Modified:** `src/data_loader.py`
- **Dependencies:** 2
- **Acceptance Criteria:** The system successfully parses and segregates clinic documents vs general medical text.

## 4. Verification & Testing
- **Description:** Write basic integration tests to verify the pipeline.
- **Files Modified:** `tests/test_rag.py`
- **Dependencies:** 3
- **Acceptance Criteria:** Tests pass verifying the PageIndex querying process.
