# 10-01 SUMMARY: Chroma Chinese Embedding Wiring & Corpus Ingestion

## Summary of Accomplishments

### 1. Chinese/Multilingual Embedding Wiring (D-01, D-02)
- Added `sentence-transformers>=6.0.0` and `opencc>=1.4.2` to `pyproject.toml` and installed via `uv sync`.
- Implemented `make_embedding_function(model_name, device)` in `src/rag/ingest.py` and passed it into Chroma's `get_or_create_collection`.
- Updated `SemanticSearch` in `src/rag/search.py` with `embedding_model` parameter and passed `make_embedding_function` to `get_collection`.
- Verified round-trip vector similarity search on Traditional Chinese text via `tests/test_chroma_wiring.py` (`1 passed in 16.50s`).

### 2. Embedding Benchmark & Config Alignment (D-02, D-03, D-04)
- Created and executed `scripts/benchmark_embedding.py` measuring latency across 20 query batches:
  - `BAAI/bge-small-zh-v1.5`: 12.14 ms / batch
  - `BAAI/bge-m3`: 96.53 ms / batch (< 300ms budget threshold)
- Selected `BAAI/bge-m3` as primary embedding model in `config/ingest_config.json`.
- Standardized collection names from `general_medical`/`clinic_specific` to `general`/`special`.
- Pointed document folders to actual source paths `data/documents/general/` and `data/documents/special/`.

### 3. API & Pipeline Synchronization (D-04 lockstep + Stage 1 Acceptance Bar)
- Updated `src/api/routes/rag.py` and `scripts/rebuild_rag.py` replacing all references to legacy collection names.
- Zero references to `general_medical` or `clinic_specific` remain in the codebase.
- Populated both Chroma collections (`general` and `special`) on disk under `data/rag/chroma/`, meeting the Stage 1 acceptance bar (`count > 0` for both).

## Verification Results
- `uv run pytest tests/test_chroma_wiring.py -x -q` -> PASS
- `config/ingest_config.json` schema validation -> PASS
- `data/rag/chroma/` collection count verification -> `general: 2`, `special: 2` -> PASS
