# 10-03 SUMMARY: Unified Chunking & Idempotent Multi-Store Ingestion

## Summary of Accomplishments

### 1. Unified Chunking & Shared `chunk_id` (D-07)
- Added guarded schema migration to `RAGEngine._init_db()`:
  - Added `chunk_id` column to `rag_chunks` table.
  - Created `rag_doc_hashes` table (`(doc_id, category)` primary key) for content-hash tracking.
- Rewrote `SimpleIndex.add_document()` to use `DocumentIngestor.chunk_text()` directly, ensuring identical token boundaries and `chunk_id` values between SQLite and Chroma.
- Maintained defensive fallback to fixed-stride chunking if no chunker is provided.

### 2. Idempotent Ingestion Pipeline (`_ingest_unified`)
- Implemented `_ingest_unified(doc, category)` in `src/rag_engine.py`:
  - Computes MD5 content hash and compares against `rag_doc_hashes`.
  - Skips unchanged documents immediately on subsequent calls (solving startup CPU re-embedding overhead).
  - Uses `collection.upsert()` for Chroma and transactional replacement for SQLite.
- Updated `ingest_special_data()` and `ingest_general_data()` to route through `_ingest_unified()`.

## Verification Results
- `tests/test_unified_chunking.py` -> **3/3 passed** (deterministic chunk IDs, hash tracking, changed content re-ingest).
- `tests/test_rag_engine.py` -> **3/3 passed** (OTC localization & reservation CTAs unaffected).
- Real Corpus Verification -> `chunk_id parity OK for 25 chunks, idempotent restart OK` (Exact ID match across SQLite & Chroma; 0 duplicate writes on unchanged restart).
