# Phase 10: RAG Retrieval Consolidation - Context

**Gathered:** 2026-08-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Merge the two disconnected RAG retrieval pipelines that currently coexist in this codebase into one hybrid (sparse + dense) retriever with Reciprocal Rank Fusion (RRF):

1. **Production path** — `SimpleIndex` in `src/rag_engine.py`: SQLite FTS5 + custom n-gram overlap scoring, no embeddings. Live — called by `hermes_core.py` (`RAGEngine.ingest_special_data` / `ingest_general_data`) and serves every real clinic chatbot answer via `RAGEngine._get_context()`.
2. **Dormant path** — `DocumentIngestor` / `SemanticSearch` in `src/rag/ingest.py` + `src/rag/search.py`: Chroma vector store, fully coded and wired to `/api/v1/rag/*` routes (`src/api/routes/rag.py`), but `data/rag/chroma/` has never been created on disk — it has never actually ingested anything.

Phase delivers: Chroma actually populated and correctly embedding Chinese text, a `HybridRetriever` (sparse+dense+RRF) swapped into the live query path with a safe fallback, one shared chunking/write path so both stores agree on chunk boundaries, and two smaller RAG-quality fixes (simplified→traditional normalization, retrieval observability logging).

**Out of scope for this phase** (see Deferred Ideas below): the `KGQA-Based-On-medicine/` nested-repo decision, `clinic.db` Git LFS migration, and auditing the `verified_training_data.jsonl` → PageIndex backflow loop — these came up in the same discussion but are independent of the retrieval-merge work.

</domain>

<decisions>
## Implementation Decisions

### Stage 1 — Make Chroma real
- **D-01:** `DocumentIngestor._init_chroma()` (`src/rag/ingest.py`) currently calls `get_or_create_collection(name=..., metadata=...)` without an `embedding_function` — the constructor's `embedding_model` param is accepted but never used, so Chroma silently falls back to its bundled English-only `all-MiniLM-L6-v2` ONNX default regardless of `config/ingest_config.json`. Fix: pass an actual `embedding_function`. — **Reversibility:** reversible — one-method code fix, no data migration.
- **D-02:** Switch the embedding model to a Chinese/multilingual one: `BAAI/bge-small-zh-v1.5` (small, CPU-friendly — this is a local server, `embedding.device` is already `"cpu"` in config) as the default; `BAAI/bge-m3` as a quality-over-latency alternative if benchmarking shows CPU latency is acceptable. Decide which at planning/implementation time by measuring actual query latency on this machine. — **Reversibility:** reversible — config value + re-embed, no schema change.
- **D-03:** `config/ingest_config.json`'s `document_folders` currently points at `data/rag/general_docs/` / `data/rag/clinic_docs/`, which are never populated — real content lives in `data/documents/general/` (848 `medical_kb_batch_*.txt`) and `data/documents/special/`. Fix the config to point at the real directories. — **Reversibility:** reversible — config only.
- **D-04:** Align naming: Chroma collections are currently `general_medical` / `clinic_specific`; SQLite categories (and the `hermes_core.py` call sites `ingest_general_data` / `ingest_special_data`) use `general` / `special`. Rename the Chroma collections to `general` / `special` to match — avoids a permanent two-name mapping table. — **Reversibility:** reversible — collection is rebuilt from source docs via `scripts/rebuild_rag.py --force` regardless.
- Verify with `scripts/rebuild_rag.py --force` and confirm `collection.count() > 0` for both collections before moving to Stage 2.

### Stage 2 — Hybrid retrieval + RRF
- **D-05:** Add a `HybridRetriever` that combines the existing `SimpleIndex.get_scored_chunks()` (sparse FTS5+n-gram — leave this function's internals untouched) with `SemanticSearch.search()` (Chroma dense) via Reciprocal Rank Fusion, and swap it in at `RAGEngine._get_context()` (`src/rag_engine.py`, the block around `rag_scored_chunks = self.special_index.get_scored_chunks(question)` / the `general_index` equivalent, ~line 579-582). Keep the existing top-4 cap and the price-redaction `re.sub` post-processing applied after fusion, unchanged.
  — **Reversibility:** reversible in the strict sense (a `git revert` fully undoes it, no data migration, no external contract) — but this is the **live query path for a production clinic chatbot answering real patients**, so the actual guard is operational, not structural: wrap all Chroma/dense calls in try/except with fallback to the current sparse-only behavior (D-06), and treat first deployment as needing a manual before/after answer-quality spot check rather than a silent swap.
- **D-06:** Chroma-call failure (timeout, model load failure, empty collection, etc.) must fall back to exactly today's sparse-only `SimpleIndex` behavior — this cannot regress or hard-fail the live chatbot. Non-negotiable acceptance bar for Stage 2.

### Stage 3 — Unify the write path
- **D-07:** `SimpleIndex.add_document()` (SQLite path, fixed 400-char stride / 600-char window, no sentence-boundary awareness) and `DocumentIngestor.chunk_text()` (sentence/paragraph-boundary-aware, section-detecting, in `src/rag/ingest.py`) currently chunk independently with different boundaries for the same source documents. Consolidate to one chunking pass — using `DocumentIngestor.chunk_text()`'s logic since it's the more correct implementation — writing the same chunk set and the same `chunk_id` to both the SQLite `rag_chunks` table and the Chroma collection, so sparse and dense hits can be correlated/deduped in the RRF step (D-05).
  — **Reversibility:** costly — existing SQLite rows use the old ad-hoc chunk boundaries/IDs; realizing this decision means a full re-ingest of both stores (`scripts/rebuild_rag.py --force` already exists for exactly this), not a live schema migration. Budget a re-ingest step; do not attempt to migrate old rows in place.

### Stage 4 — Remaining book-to-skil.md gaps
- **D-08:** Add a Simplified→Traditional Chinese normalization pass before ingesting the 848 `medical_kb_batch_*.txt` files (confirmed simplified-character source, e.g. `data/documents/general/medical_kb_batch_1.txt`). The clinic system prompt in `RAGEngine.query_integrated()` hard-requires `嚴禁簡體中文` in output — raw simplified source text risks leaking into answers verbatim via retrieved chunks. — **Reversibility:** reversible.
- **D-09:** Add lightweight retrieval observability: log which chunk ids + fused scores were actually used to construct each answer (extends the existing `logger.info` instrumentation already present throughout `_get_context()` — this phase adds chunk-level detail, not a new logging subsystem). Purpose: distinguish "bad retrieval" from "bad LLM reasoning" when debugging a wrong answer. — **Reversibility:** reversible.

### Claude's Discretion
- Exact RRF constant (`k`, typically 60 in the literature) and exact top-N per retriever before fusion (sparse currently pulls top-30 via FTS5 `LIMIT 30`; dense top-N to decide) — implementer's call, informed by research in this phase.
- Whether `bge-small-zh-v1.5` or `bge-m3` ships as the default — decide from measured CPU latency, not guesswork.
- Whether Stage 3's re-ingest runs as part of this phase's verification or is deferred to a follow-up maintenance task — implementer's call based on how large the re-ingest turns out to be.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### RAG best-practices source
- `book-to-skil.md` (repo root) — user-supplied notebook export on medical RAG best practices; this phase directly implements its "hybrid BM25 + dense + RRF fusion" and "structure-aware chunking" recommendations (steps 3-4 of the notebook's 6-step medical RAG implementation guide). Also references BGE-M3 by name as the recommended dense embedding model.

### Existing RAG code (this phase's primary surface)
- `src/rag_engine.py` — `RAGEngine`, `SimpleIndex`, `ReasonerWrapper`. Production query path (`query_integrated`, `_get_context`) and the two production categories `special`/`general`. PageIndex reasoning trees and `GraphRAGEngine` integration live here too — **do not touch**, out of scope.
- `src/rag/ingest.py` — `DocumentIngestor`, `ChunkResult`, `IngestResult`. The dormant Chroma path. Has the dead `embedding_model` param (D-01) and the working `chunk_text()` sentence-boundary chunker (reused in D-07).
- `src/rag/search.py` — `SemanticSearch`, `SearchResult`. Chroma query interface (`.search()`), distance→similarity conversion.
- `src/rag/graph_rag_engine.py` — `GraphRAGEngine`. Separate knowledge-graph context source, already integrated into `_get_context()`. Not touched by this phase.
- `src/api/routes/rag.py` — `/api/v1/rag/*` Flask blueprint; loads `config/ingest_config.json` via `load_config()`.
- `config/ingest_config.json` — Chroma path/collections, `document_folders`, chunking params, embedding model/device — source of D-02/D-03/D-04 fixes.
- `scripts/rebuild_rag.py` — existing CLI to batch re-ingest a Chroma collection from a docs directory; reused as-is for Stage 1 verification and Stage 3's re-ingest.
- `src/agent/hermes_core.py` — calls `self.rag.ingest_special_data(special_docs)` / `ingest_general_data(general_docs)`; the real production write entry point that Stage 3's unified write path must go through.

### Data
- `data/documents/general/medical_kb_batch_*.txt` (848 files, untracked, Simplified Chinese) — Stage 1's real ingest target, Stage 4's normalization target.
- `data/documents/special/` — the clinic-specific real ingest target (mirrors `data/archive/` marketing assets kept during the earlier stash-conflict resolution this session; not documents themselves).

No external specs beyond the notebook above — requirements fully captured in the Implementation Decisions.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DocumentIngestor.chunk_text()` (`src/rag/ingest.py:321-407`) — already does sentence/paragraph-boundary-aware chunking with section detection; this becomes the single chunker for Stage 3 instead of `SimpleIndex.add_document()`'s crude fixed-stride slicing.
- `SimpleIndex.get_scored_chunks()` (`src/rag_engine.py`) — FTS5 bm25 + custom n-gram scoring; kept as-is as the sparse half of `HybridRetriever`.
- `scripts/rebuild_rag.py` — batch ingest CLI already exists; reuse for Stage 1 verification and any Stage 3 re-ingest, after fixing its target directories (D-03) and collection names (D-04).

### Established Patterns
- Defensive `try/except` around every DB/LLM call with a logged fallback, throughout `rag_engine.py` — `HybridRetriever`'s Chroma fallback (D-06) should match this existing style, not introduce a new error-handling convention.
- Post-retrieval regex redaction of prices/amounts (`re.sub(r'\$\s*\d+...')` etc.) applied to `rag_context`/`graph_context` before they reach the LLM prompt — must still run on whatever `HybridRetriever` returns, in the same place in `_get_context()`.

### Integration Points
- `RAGEngine._get_context()` (`src/rag_engine.py`, ~line 577-596) — exact swap point for `HybridRetriever` (Stage 2).
- `RAGEngine.ingest_special_data` / `ingest_general_data` (~line 242-254) — write-path entry point Stage 3 must route through so both stores get the same chunk set.
- `src/api/routes/rag.py` — already exposes `/api/v1/rag/search` and `/api/v1/rag/ingest` against the Chroma-only path; once Chroma is actually populated (Stage 1) these routes become truthful for the first time, worth a quick sanity check but not a rewrite target.

</code_context>

<specifics>
## Specific Ideas

- Embedding model candidates named explicitly by the user's own analysis: `BAAI/bge-small-zh-v1.5` (CPU-friendly default) or `BAAI/bge-m3` (higher quality, higher latency) — pick based on measured latency, not assumption.
- RRF (Reciprocal Rank Fusion) is the specified fusion method, not a weighted linear blend — matches book-to-skil.md's "RRF & Reranker" recommendation.
- Keep the existing top-4 chunk cap and price-redaction regex post-processing exactly as they are today — this phase changes *which* chunks win, not the shape of what gets passed to the LLM prompt.

</specifics>

<deferred>
## Deferred Ideas

### Reviewed Todos (not folded)
- **`KGQA-Based-On-medicine/` nested-repo decision** (it carries its own `.git/`, currently untracked in the main repo) — whether to extract its RDF/Fuseki triples into the existing `GraphRAGEngine` graph db or drop it. Deferred: independent of the retrieval-merge work; touches `GraphRAGEngine`, which this phase explicitly does not modify.
- **`data/db/clinic.db` Git LFS migration** — GitHub already warned on push this session that the 72MB `clinic.db` exceeds its recommended file size. Deferred: a repo-hygiene/CI concern, unrelated to retrieval logic.
- **`verified_training_data.jsonl` → PageIndex backflow loop audit** — confirming `RAGEngine.inject_verified_knowledge()` actually closes the loop from physician corrections back into ranked retrieval. Deferred: PageIndex is explicitly out of scope for this phase (see Phase Boundary); worth its own phase once Stage 2's hybrid retriever is stable.

</deferred>

---

*Phase: 10-RAG Retrieval Consolidation*
*Context gathered: 2026-08-25*
