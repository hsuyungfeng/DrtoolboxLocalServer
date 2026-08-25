# Phase 10: RAG Retrieval Consolidation - Research

**Researched:** 2026-08-25
**Domain:** Hybrid retrieval (sparse SQLite FTS5 + dense Chroma embeddings) with Reciprocal Rank Fusion, Chinese medical text normalization
**Confidence:** HIGH (installed-package APIs and in-repo code all read directly this session) / MEDIUM (embedding-model latency and quality claims, sourced from web search, not benchmarked on this exact model+CPU combination)

## Summary

This phase merges two RAG pipelines that already exist in the codebase: the live SQLite FTS5 + n-gram sparse retriever (`SimpleIndex` in `src/rag_engine.py`) and a fully-coded but never-populated Chroma dense pipeline (`DocumentIngestor`/`SemanticSearch` in `src/rag/`). Both halves of the merge are concrete, well-scoped code fixes — no new frameworks are being introduced. The four discretion questions the user flagged (chromadb embedding_function wiring, bge-small-zh-v1.5 vs bge-m3, RRF formula, Simplified→Traditional conversion) are all answered below with the exact installed-version APIs, not generic training-data guesses — the installed `chromadb` is 1.5.9 (not the `>=0.4.0` floor in `pyproject.toml`), which matters because the `embedding_function` parameter and `SentenceTransformerEmbeddingFunction` class were read directly from the installed package source this session.

Three findings not explicitly called out in CONTEXT.md but load-bearing for planning: (1) `src/api/routes/rag.py` hardcodes the *old* collection names (`general_medical`/`clinic_specific`) as request-parameter defaults and config lookup keys — D-04's rename will silently break `/api/v1/rag/*` unless this file's defaults are updated too, even though CONTEXT.md scoped it as "quick sanity check, not a rewrite target." (2) `HermesAgent._initial_ingest()` re-walks and re-ingests **all** `data/documents/{general,special}/` files (1,726 files today, growing via background OCR) on **every server startup** with no content-hash skip logic — wiring naive Chroma writes into this same path (Stage 3) would re-embed the entire corpus on every restart unless the ingest step is made idempotent (skip-if-unchanged or `upsert`). (3) `SimpleIndex.get_scored_chunks()` returns `(score, content_text)` tuples with **no chunk id** — RRF needs a correlation key between the sparse and dense result lists, and until Stage 3 unifies the chunking pass, sparse and dense chunks for the same source text will have different boundaries, so true ID-based dedup isn't available until Stage 3 lands; Stage 2's `HybridRetriever` should key on a content-hash for best-effort dedup and treat everything else as position-only RRF.

**Primary recommendation:** Fix Chroma wiring with `chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction(model_name="BAAI/bge-small-zh-v1.5", device="cpu")` passed as `embedding_function=` to `get_or_create_collection()`; add `sentence-transformers` and `opencc` (the official `BYVoid/OpenCC` PyPI binding) to `pyproject.toml`; implement RRF as a small pure-Python function keyed on the union of sparse-list and dense-list items (content-hash correlation, k=60); and make Stage 3's unified write path idempotent against the startup re-ingest loop before wiring Chroma writes into it.

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `DocumentIngestor._init_chroma()` (`src/rag/ingest.py`) currently calls `get_or_create_collection(name=..., metadata=...)` without an `embedding_function` — fix by passing an actual `embedding_function`. Reversible — one-method code fix, no data migration.
- **D-02:** Switch the embedding model to a Chinese/multilingual one: `BAAI/bge-small-zh-v1.5` (small, CPU-friendly, `embedding.device` already `"cpu"` in config) as default; `BAAI/bge-m3` as a quality-over-latency alternative if benchmarking shows CPU latency is acceptable. Decide at planning/implementation time by measuring actual query latency on this machine. Reversible — config value + re-embed, no schema change.
- **D-03:** `config/ingest_config.json`'s `document_folders` currently points at `data/rag/general_docs/`/`data/rag/clinic_docs/` (never populated) — fix to point at `data/documents/general/` and `data/documents/special/`. Reversible — config only.
- **D-04:** Rename Chroma collections `general_medical`/`clinic_specific` → `general`/`special` to match SQLite category names and `hermes_core.py` call sites. Reversible — collection rebuilt from source via `scripts/rebuild_rag.py --force` regardless.
- Verify with `scripts/rebuild_rag.py --force` and confirm `collection.count() > 0` for both collections before Stage 2.
- **D-05:** Add a `HybridRetriever` combining `SimpleIndex.get_scored_chunks()` (sparse, unchanged) with `SemanticSearch.search()` (Chroma dense) via RRF, swapped into `RAGEngine._get_context()` (~line 577-596). Keep the existing top-4 cap and price-redaction `re.sub` post-processing applied after fusion, unchanged. Reversibility is structural-only (`git revert` undoes it cleanly), but the actual guard is operational: this is the live query path for a production clinic chatbot, so wrap Chroma calls in try/except with sparse-only fallback (D-06) and treat first deployment as needing a manual before/after answer-quality spot check.
- **D-06:** Chroma-call failure (timeout, model load failure, empty collection, etc.) must fall back to exactly today's sparse-only `SimpleIndex` behavior — non-negotiable acceptance bar for Stage 2, cannot regress or hard-fail the live chatbot.
- **D-07:** Consolidate `SimpleIndex.add_document()` (fixed 400-char stride/600-char window) and `DocumentIngestor.chunk_text()` (sentence/paragraph-boundary-aware) to one chunking pass using `DocumentIngestor.chunk_text()`'s logic, writing the same chunk set and same `chunk_id` to both SQLite `rag_chunks` and the Chroma collection. Costly reversal — existing SQLite rows use old ad-hoc boundaries/IDs; realizing this decision requires a full re-ingest via `scripts/rebuild_rag.py --force`, not a live migration. Budget a re-ingest step; do not migrate old rows in place.
- **D-08:** Add a Simplified→Traditional Chinese normalization pass before ingesting the `data/documents/general/` corpus (confirmed Simplified source). The clinic system prompt in `RAGEngine.query_integrated()` hard-requires `嚴禁簡體中文` in output — raw simplified source text risks leaking into answers verbatim via retrieved chunks. Reversible.
- **D-09:** Add lightweight retrieval observability: log which chunk ids + fused scores were used to construct each answer, extending existing `logger.info` instrumentation in `_get_context()` — chunk-level detail, not a new logging subsystem. Reversible.

### Claude's Discretion

- Exact RRF constant `k` (typically 60 in the literature) and exact top-N per retriever before fusion (sparse currently pulls top-30 via FTS5 `LIMIT 30`; dense top-N to decide) — implementer's call, informed by this research.
- Whether `bge-small-zh-v1.5` or `bge-m3` ships as the default — decide from measured CPU latency, not guesswork.
- Whether Stage 3's re-ingest runs as part of this phase's verification or is deferred to a follow-up maintenance task — implementer's call based on how large the re-ingest turns out to be.

### Deferred Ideas (OUT OF SCOPE)

- `KGQA-Based-On-medicine/` nested-repo decision (its own `.git/`, untracked in main repo) — whether to extract RDF/Fuseki triples into `GraphRAGEngine`. Deferred: touches `GraphRAGEngine`, which this phase explicitly does not modify.
- `data/db/clinic.db` Git LFS migration (72MB file, GitHub warned on push). Deferred: repo-hygiene/CI concern, unrelated to retrieval logic.
- `verified_training_data.jsonl` → PageIndex backflow loop audit (`RAGEngine.inject_verified_knowledge()`). Deferred: PageIndex explicitly out of scope for this phase; worth its own phase once the hybrid retriever is stable.

## Phase Requirements

No requirement IDs from REQUIREMENTS.md map to this phase — REQUIREMENTS.md (Epic 1: Knowledge Base & RAG Engine, RQ-1.1–1.3; Epic 2: Data Logging, RQ-2.1–2.2; Epic 3: Web Dashboard, RQ-3.1–3.2) predates this phase, which originated from a direct codebase audit (confirmed: RQ-1.1 "Implement PageIndex vectorless reasoning RAG architecture" and RQ-1.2 "data ingestion pipeline to segregate Clinic Special Data from General Medical Data" are both already implemented by the existing `RAGEngine`/`SimpleIndex`/PageIndex code this phase builds on top of — no new requirement IDs are introduced by this phase). Per the phase description, "Phase requirement IDs (MUST address): none."

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Sparse (FTS5+n-gram) retrieval | API/Backend — `src/rag_engine.py` (`SimpleIndex`) | Database/Storage — SQLite `rag_chunks`/`rag_chunks_fts` | Already lives entirely in the backend query layer; untouched by this phase (D-05 says "leave internals untouched"). |
| Dense (embedding) retrieval | API/Backend — `src/rag/search.py` (`SemanticSearch`) | Database/Storage — Chroma `PersistentClient` on disk at `data/rag/chroma/` | Chroma is an embedded vector store, not a separate service; queries execute in-process from the Flask backend. |
| Embedding generation | API/Backend — `chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction` (loads `sentence-transformers` model into process memory) | — | CPU-bound in-process inference; no external embedding API call. Runs on the same host as the LLM (`llama-cpp-python`), competing for CPU/RAM per D-02's framing. |
| RRF fusion | API/Backend — new `HybridRetriever` (this phase) | — | Pure computation over two already-retrieved ranked lists; no I/O of its own. |
| Chunking (ingest-time) | API/Backend — `DocumentIngestor.chunk_text()` (becomes the single chunker per D-07) | Database/Storage — writes to both SQLite and Chroma | Chunking is a data-transformation step feeding two storage backends; the transformation itself is backend logic. |
| Simplified→Traditional normalization | API/Backend — new pre-ingest pass (D-08), likely inside `DocumentIngestor`/ingest scripts | — | Pure text transformation before chunking; belongs in the ingestion pipeline, not the query path. |
| Retrieval observability logging | API/Backend — extends existing `logger.info` in `_get_context()` | — | Logging is a backend cross-cutting concern; D-09 explicitly says extend, not build new subsystem. |
| `/api/v1/rag/*` HTTP surface | API/Backend — `src/api/routes/rag.py` (Flask blueprint) | — | Thin HTTP wrapper; becomes "truthful" once Chroma is populated (Stage 1) but its hardcoded old collection-name defaults are a coupling risk for D-04 (see Common Pitfalls). |

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `chromadb` | 1.5.9 installed [VERIFIED: `.venv/bin/python3 -c "import chromadb; print(chromadb.__version__)"` — this session] | Persistent local vector store | Already a project dependency (`pyproject.toml: "chromadb>=0.4.0"`); already wired (just not fed an embedding function). Do not swap vector stores. |
| `sentence-transformers` | 6.0.0 latest on PyPI [VERIFIED: PyPI JSON API `https://pypi.org/pypi/sentence-transformers/json` — this session; **not currently installed** in `.venv`, confirmed via `import sentence_transformers` → `ModuleNotFoundError` this session] | Loads HuggingFace embedding models (BGE family) for Chroma's `SentenceTransformerEmbeddingFunction` | Chroma's own bundled `SentenceTransformerEmbeddingFunction` (`chromadb/utils/embedding_functions/sentence_transformer_embedding_function.py`, read this session) hard-requires this package — `from sentence_transformers import SentenceTransformer` inside its `__init__`, raising `ValueError` if missing. Must be added to `pyproject.toml`. |
| `opencc` (PyPI package name `OpenCC`, import name `opencc`) | 1.4.2 latest on PyPI, 21 releases since 2014 [VERIFIED: PyPI JSON API — this session; **not currently installed**] | Simplified→Traditional Chinese conversion (D-08) | Official `BYVoid/OpenCC` Python binding — the canonical library for this exact task in the Chinese-NLP ecosystem, with a Taiwan-phrase-aware config (`s2twp`) that matches this clinic's Taiwan-Traditional output requirement (`嚴禁簡體中文` in the system prompt). |

### Supporting

| Library | Version | Purpose | When to Use |
|---------|---------|---------|-------------|
| `torch` | 2.12.0+cu130 installed [VERIFIED: `.venv/bin/python3 -c "import torch; print(torch.__version__)"` — this session] | Backend for `sentence-transformers` model inference | Already a project dependency; CUDA-capable (`torch.cuda.is_available()` → `True`, device `NVIDIA GeForce RTX 2080 Ti`, ~23GB VRAM [VERIFIED: `.venv/bin/python3 -c "import torch; print(torch.cuda.is_available())"` — this session]) but `config/ingest_config.json`'s `embedding.device` is locked to `"cpu"` per D-02 to avoid contending with the LLM's GPU usage — do not silently move embeddings to GPU without a separate decision. |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction` | Custom `EmbeddingFunction` subclass calling `sentence_transformers.SentenceTransformer` directly | No benefit — Chroma's built-in class already does exactly this with model caching (`models: Dict[str, Any] = {}` class-level cache avoids reloading the model per collection); hand-rolling would duplicate it for no gain. |
| `BAAI/bge-m3` for all queries | `BAAI/bge-small-zh-v1.5` for all queries | See Standard Stack "Core" and D-02 discussion below — this is the explicit discretion decision this research informs, not a settled recommendation. |
| `opencc` (BYVoid binding) | `opencc-python-reimplemented` (pure-Python reimplementation, no C++ dependency) | `opencc-python-reimplemented` avoids needing OpenCC's compiled dictionaries/shared library but is a community reimplementation, not the canonical upstream project, and has a much smaller release history (fewer maintenance signals). Prefer `opencc` unless the C++ binding fails to build in this environment. |

**Installation:**
```bash
uv pip install "sentence-transformers>=6.0.0" "opencc>=1.4.2"
# or, if adding to pyproject.toml:
# dependencies += ["sentence-transformers>=6.0.0", "opencc>=1.4.2"]
```

**Version verification performed this session:**
- `chromadb`: installed 1.5.9 == PyPI latest 1.5.9 [VERIFIED: `.venv/bin/python3 -c "import chromadb; print(chromadb.__version__)"` + PyPI JSON API cross-check]
- `sentence-transformers`: not installed; PyPI latest 6.0.0, released 2026-08-18 [VERIFIED: PyPI JSON API]
- `opencc` (PyPI name `OpenCC`): not installed; PyPI latest 1.4.2, released 2026-08-22, 21 releases since 2014-08-02 [VERIFIED: PyPI JSON API]
- `torch`: installed 2.12.0+cu130 [VERIFIED: `.venv/bin/python3 -c "import torch; print(torch.__version__)"`]

Note the `pyproject.toml` floor `"chromadb>=0.4.0"` is stale by more than a year of releases (0.4.0 → 1.5.9, 130 total releases [VERIFIED: PyPI JSON API]) — the installed API surface (e.g. `get_or_create_collection`'s `embedding_function` default value, `Collection` construction) reflects the 1.x rewrite, not the 0.4.x API most training-data code examples target. All code examples in this document were verified against the actually-installed 1.5.9 source, not against generic 0.4.x-era chromadb tutorials.

## Package Legitimacy Audit

`gsd-tools query package-legitimacy check` was not available in the installed `gsd-tools` version in this environment (command not found — `Unknown command: query`); the equivalent registry checks below were performed manually via direct PyPI JSON API queries this session, which is the same underlying signal source the seam would use.

| Package | Registry | Age | Releases | Source Repo | Verdict | Disposition |
|---------|----------|-----|----------|-------------|---------|-------------|
| `sentence-transformers` | PyPI | 7 yrs (first release 2019-07-25) | 82 | github.com/huggingface/sentence-transformers | OK | Approved |
| `chromadb` | PyPI | 3.5 yrs (first release 2023-02-09) | 130 | github.com/chroma-core/chroma | OK | Approved (already installed/pinned) |
| `opencc` (PyPI name `OpenCC`) | PyPI | 12 yrs (first release 2014-08-02) | 21 | github.com/BYVoid/OpenCC | OK | Approved |

All three packages have long-lived, actively-maintained, canonical upstream GitHub repositories under well-known organizational/individual accounts (Hugging Face, Chroma's own org, and BYVoid the long-standing OpenCC author) — none of the SLOP/SUS risk signals (near-zero release history, no source repo, recently-registered name) apply. **Packages removed due to [SLOP] verdict:** none. **Packages flagged as suspicious [SUS]:** none.

`BAAI/bge-small-zh-v1.5` and `BAAI/bge-m3` are Hugging Face model repositories, not PyPI packages — the package-legitimacy protocol applies to installable code packages; these are downloaded weights fetched at runtime by `sentence-transformers`/`huggingface_hub` on first use. Model provenance was checked via the official Hugging Face model cards (see Sources) rather than the PyPI legitimacy gate.

## Architecture Patterns

### System Architecture Diagram

```
                         User query (LINE/Web chat)
                                    │
                                    ▼
                    HermesAgent → RAGEngine.query_integrated()
                                    │
                                    ▼
                    RAGEngine._get_context(question, route)
                    ┌───────────────┼───────────────────────┐
                    │               │                       │
                    ▼               ▼                       ▼
            SQL context      PageIndex context      HybridRetriever (NEW)
         (structured HIS)    (reasoning trees)               │
                                                ┌──────────────┴──────────────┐
                                                ▼                             ▼
                                  SimpleIndex.get_scored_chunks()   SemanticSearch.search()
                                  (SQLite FTS5 + n-gram, sparse)    (Chroma dense, embedding
                                       category="special"/           via bge-small-zh/bge-m3)
                                       "general"                    collection="special"/"general"
                                                │                             │
                                                │        try/except ─────────┘
                                                │        (D-06: on Chroma failure,
                                                │         fall back to sparse-only)
                                                ▼
                                    Reciprocal Rank Fusion (k=60)
                                    fuse(sparse_ranked, dense_ranked)
                                    → correlate by content-hash where
                                      possible, else rank-only fusion
                                                │
                                                ▼
                                   top-4 cap + price-redaction re.sub
                                   (unchanged post-processing, D-05)
                                                │
                                                ▼
                                        rag_context string
                                                │
                                                ▼
                              (combined with sql_context, pi_context,
                               graph_context) → LLM prompt → answer
                                                │
                                                ▼
                          D-09: log chunk_ids + fused scores used
                                (extends existing logger.info calls)


Ingestion (separate pipeline, Stage 1/3):
  data/documents/general/*.txt (848+ files, Simplified Chinese)
  data/documents/special/*.txt (878+ files, mixed Simplified/Traditional/OCR)
            │
            ▼
  D-08: OpenCC s2twp normalization pass (Simplified → Traditional-Taiwan)
            │
            ▼
  D-07: DocumentIngestor.chunk_text() — single chunking pass,
        shared chunk_id generation
            │
      ┌─────┴─────┐
      ▼           ▼
  SQLite        Chroma
  rag_chunks    collection.add() / upsert()
  (same chunk_id as Chroma, per D-07)
```

### Recommended Project Structure

No new top-level directories — this phase modifies existing files in place:
```
src/
├── rag_engine.py          # RAGEngine, SimpleIndex — add HybridRetriever here or as new src/rag/hybrid.py
├── rag/
│   ├── ingest.py           # DocumentIngestor — fix _init_chroma() (D-01), reuse chunk_text() (D-07)
│   ├── search.py           # SemanticSearch — unchanged, consumed by HybridRetriever
│   ├── hybrid.py           # NEW (suggested) — HybridRetriever + RRF fusion function
│   └── normalize.py        # NEW (suggested) — OpenCC s2twp wrapper for D-08
├── api/routes/rag.py       # Update hardcoded 'general_medical'/'clinic_specific' defaults (see pitfall)
config/
└── ingest_config.json      # D-03 (document_folders), D-04 (collection names), D-02 (embedding.model)
scripts/
└── rebuild_rag.py          # Reused as-is for Stage 1 verification and Stage 3 re-ingest
```

### Pattern 1: Wiring a custom embedding_function into Chroma (D-01, D-02)

**What:** Pass an explicit `EmbeddingFunction` instance to `get_or_create_collection()` instead of relying on Chroma's bundled English-only default.
**When to use:** `DocumentIngestor._init_chroma()` and any other code path that creates/gets a Chroma collection for Chinese content (including `SemanticSearch._init_client()`'s `get_collection()` call — note `get_collection()` does not take an `embedding_function` in the same way; Chroma persists the embedding function config with the collection at creation time and validates on later `get_collection()` calls that a passed-in function doesn't conflict with what's stored).
**Example:**
```python
# Source: chromadb/utils/embedding_functions/sentence_transformer_embedding_function.py
# and chromadb/api/client.py, read directly from installed chromadb==1.5.9 this session.
from chromadb.utils import embedding_functions

ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="BAAI/bge-small-zh-v1.5",  # or "BAAI/bge-m3" per D-02 latency decision
    device="cpu",                          # matches config/ingest_config.json embedding.device
)

self.collection = self.client.get_or_create_collection(
    name=self.collection_name,             # "general" / "special" per D-04
    metadata={"description": "Medical documents for RAG"},
    embedding_function=ef,                  # <-- the missing piece (D-01)
)
```
Verbatim signature confirmed this session from `.venv/lib/python3.12/site-packages/chromadb/api/client.py:319-329`:
```
def get_or_create_collection(
    self,
    name: str,
    schema: Optional[Schema] = None,
    configuration: Optional[CreateCollectionConfiguration] = None,
    metadata: Optional[CollectionMetadata] = None,
    embedding_function: Optional[
        EmbeddingFunction[Embeddable]
    ] = DefaultEmbeddingFunction(),  # type: ignore
    data_loader: Optional[DataLoader[Loadable]] = None,
) -> Collection:
```
[VERIFIED: `.venv/lib/python3.12/site-packages/chromadb/api/client.py:319-329` — read this session]

And `SentenceTransformerEmbeddingFunction.__init__` verbatim, confirming the `sentence_transformers` hard dependency and the model-caching behavior:
```
def __init__(
    self,
    model_name: str = "all-MiniLM-L6-v2",
    device: str = "cpu",
    normalize_embeddings: bool = False,
    **kwargs: Any,
):
    try:
        from sentence_transformers import SentenceTransformer
    except ImportError:
        raise ValueError(
            "The sentence_transformers python package is not installed. Please install it with `pip install sentence_transformers`"
        )
    ...
    if model_name not in self.models:
        self.models[model_name] = SentenceTransformer(
            model_name_or_path=model_name, device=device, **kwargs
        )
    self._model = self.models[model_name]
```
[VERIFIED: `.venv/lib/python3.12/site-packages/chromadb/utils/embedding_functions/sentence_transformer_embedding_function.py:13-47` — read this session]

The `models` dict is a **class attribute**, not instance attribute — so instantiating `SentenceTransformerEmbeddingFunction` twice with the same `model_name` (e.g. once for the "general" collection, once for "special") reuses the already-loaded model in process memory rather than double-loading it. Important for `SemanticSearch`, which also needs an embedding function passed at `_init_client()`'s `client.get_collection(name=...)` call — `get_collection` must be given the same embedding function used at creation, or Chroma will use whatever was persisted; passing a mismatched one raises a validation error (`validate_embedding_function_conflict_on_get`, seen in `client.py`).

### Pattern 2: Reciprocal Rank Fusion for two differently-shaped ranked lists

**What:** RRF assigns `score = Σ 1/(k + rank)` for each item across the lists it appears in, then sorts descending by summed score. It requires each item to have a *stable identity* the algorithm can use to detect "this item appeared in both lists."
**When to use:** Fusing `SimpleIndex.get_scored_chunks()` output (`List[Tuple[score, content_str]]`, no chunk id) with `SemanticSearch.search()` output (`List[SearchResult]`, has `.id`, `.text`, `.metadata`).
**The correlation-key problem (this phase's actual hard part):** Until Stage 3 (D-07) unifies chunking, sparse and dense chunks for the same source document have *different* text boundaries — so there is no shared `chunk_id` to fuse on yet in Stage 2. The pragmatic interim key is a hash of the chunk's own text content: two chunks are "the same item" for fusion purposes only if their text is identical (which will rarely happen pre-Stage-3, meaning Stage 2's RRF mostly behaves as a rank-interleave rather than a true fusion-with-dedup — this is expected and acceptable per D-05's staged rollout). After Stage 3, both stores share the real `chunk_id`, and fusion should switch to using that as the key.
**Example:**
```python
# Reciprocal Rank Fusion — formula and k=60 default per
# Cormack et al. 2009 (canonical RRF paper), corroborated by Elastic's
# RRF documentation (https://www.elastic.co/guide/en/elasticsearch/reference/8.19/rrf.html)
# [CITED: elastic.co/guide/en/elasticsearch/reference/8.19/rrf.html]
import hashlib
from typing import List, Tuple

def _key(text: str) -> str:
    """Best-effort correlation key pre-Stage-3; becomes chunk_id post-Stage-3."""
    return hashlib.md5(text.strip().encode("utf-8")).hexdigest()

def reciprocal_rank_fusion(
    sparse_ranked: List[Tuple[float, str]],   # (score, content) from get_scored_chunks(), already sorted desc
    dense_ranked: List[str],                  # content strings from SemanticSearch.search(), already sorted by similarity desc
    k: int = 60,
) -> List[str]:
    """Fuse two pre-ranked lists into one, returning content strings ranked by fused score."""
    fused_scores: dict[str, float] = {}
    content_by_key: dict[str, str] = {}

    for rank, (_score, content) in enumerate(sparse_ranked, start=1):
        key = _key(content)
        fused_scores[key] = fused_scores.get(key, 0.0) + 1.0 / (k + rank)
        content_by_key[key] = content

    for rank, content in enumerate(dense_ranked, start=1):
        key = _key(content)
        fused_scores[key] = fused_scores.get(key, 0.0) + 1.0 / (k + rank)
        content_by_key[key] = content

    ranked_keys = sorted(fused_scores, key=lambda kk: fused_scores[kk], reverse=True)
    return [content_by_key[kk] for kk in ranked_keys]
```
[VERIFIED: RRF formula structure cross-checked against `pip`-equivalent registry-grade source — Elasticsearch official docs, `k` default = 60] [CITED: elastic.co]

### Pattern 3: Simplified→Traditional (Taiwan) normalization with OpenCC (D-08)

**What:** Convert Simplified Chinese source text to Traditional Chinese with Taiwan-standard phrasing before chunking/ingestion, so retrieved chunks never leak Simplified characters or Mainland phrasing into answers.
**When to use:** As a pre-ingest pass over `data/documents/general/` (confirmed Simplified — sampled `medical_kb_batch_1.txt` this session: `【疾病描述】：肺泡蛋白质沉积症(简称PAP)...`, using Simplified characters `简称`/`该病` etc. [VERIFIED: `data/documents/general/medical_kb_batch_1.txt` — read this session]) and optionally `data/documents/special/`, which was sampled and found to be a **mix** of Simplified, Traditional, and OCR-garbled text (see Common Pitfalls).
**Example:**
```python
# Source: BYVoid/OpenCC official Python binding usage (github.com/BYVoid/OpenCC)
# s2twp = Simplified -> Traditional (Taiwan standard) WITH Taiwan-idiom phrase substitution
# (not just character-level conversion) — matches this clinic's Taiwan-Traditional requirement.
# [CITED: github.com/BYVoid/OpenCC, data/config/s2twp.json]
from opencc import OpenCC

_converter = OpenCC('s2twp')

def normalize_to_traditional(text: str) -> str:
    return _converter.convert(text)
```

### Anti-Patterns to Avoid

- **Re-embedding the whole corpus on every server restart:** `HermesAgent._initial_ingest()` (`src/agent/hermes_core.py:48-56`) calls `get_special_data`/`get_general_data` → `process_and_load_directory()` (`src/data_loader.py:211`), which globs **every** `.txt` file under `data/documents/{general,special}/` on every app startup with no content-hash/skip-if-unchanged check [VERIFIED: `src/data_loader.py:211-224` — read this session, shows unconditional `glob.glob(... "**/*.txt")` read+append loop with no existence/hash check before calling `rag_engine_instance` ingestion]. `SimpleIndex.add_document()` already tolerates this (its SQLite write is a cheap `DELETE`+`INSERT`). If Stage 3 wires Chroma writes into this same path without idempotency, every restart re-embeds ~1,726+ documents on CPU. Use `collection.upsert()` (which Chroma supports as an alternative to `add()`) or a content-hash-gated skip before calling `ingest()`.
- **Assuming `src/api/routes/rag.py` doesn't need touching:** it hardcodes `'general_medical'`/`'clinic_specific'` as the default `collection` request parameter and as the config-lookup key into `config["chroma"]["collections"]` (`get_ingestor()`, `get_query_answer()` — `src/api/routes/rag.py:52-121`) [VERIFIED: `src/api/routes/rag.py:52-121` — read this session]. After D-04 renames the actual Chroma collections to `general`/`special`, these defaults become stale (requests without an explicit `collection` param will look up a collection name that no longer exists in `config/ingest_config.json`'s post-D-03/D-04 collections map). Not a rewrite, but the defaults and the `config["chroma"]["collections"]` keys must be updated in lockstep with D-04.
- **Fusing on chunk_id before Stage 3:** see Pattern 2 above — building `HybridRetriever` assuming a shared `chunk_id` exists between sparse and dense results before Stage 3's unification will silently produce an empty-intersection fusion (every item looks unique) with no error raised. Use content-hash correlation as the interim key.
- **Loading `sentence-transformers` model weights synchronously on the request path:** first-call model load (from Hugging Face Hub, since neither model is currently cached locally — no `~/.cache/huggingface` presence checked, and network fetch is required on first use) could take tens of seconds. Load-and-warm the embedding model at `RAGEngine.__init__()` or `DocumentIngestor` startup, not inside `_get_context()`'s request path, mirroring how `llm_instance` is already a module-level singleton in `src/llm_server.py`.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Chinese-model-aware text embedding | A custom ONNX/ HF Hub download + tokenize + pool + batch pipeline | `chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction` | Already handles model caching (class-level `models` dict), batching, numpy conversion, and Chroma's `EmbeddingFunction` protocol (`__call__`, `name()`, `default_space()`, config serialization for persistence) — read directly from the installed package this session; reimplementing any of this is pure risk for zero benefit. |
| Simplified→Traditional conversion | A custom character-mapping dict or regex table | `opencc` (`OpenCC('s2twp')`) | Character-only mapping tables miss word/phrase-level conversions (Taiwan medical terminology differs from Mainland at the vocabulary level, not just glyph level, per the `s2twp` config's explicit purpose) and miss context-dependent character disambiguation (some Simplified characters map to different Traditional characters depending on the word). OpenCC's dictionaries encode exactly this. |
| Reciprocal Rank Fusion | A weighted linear blend of normalized sparse/dense scores | The RRF formula in Pattern 2 | book-to-skil.md and CONTEXT.md's D-05 both specify RRF explicitly, not a weighted blend — RRF avoids needing to normalize two incomparable score scales (BM25/n-gram scores vs cosine similarity) onto the same range, which a weighted blend would require and which is a well-known source of tuning fragility. |

**Key insight:** Every piece of this phase already has a battle-tested off-the-shelf answer (Chroma's own embedding-function class, OpenCC, the standard RRF formula) — the actual engineering work is *wiring*, not *building*: passing the right parameter, adding the right dependency, writing ~20 lines of fusion glue code, and getting the idempotency/sequencing right across Stage 2 (before unification) vs Stage 3 (after unification).

## Common Pitfalls

### Pitfall 1: Startup re-ingestion cost explosion (see Anti-Patterns above for detail)
**What goes wrong:** Every Flask process start triggers a full walk + read + (post-Stage-3) re-embed of the entire document corpus.
**Why it happens:** `_initial_ingest()` has no persistence-aware skip logic; it was written when the write path only touched cheap SQLite `DELETE`+`INSERT`.
**How to avoid:** Gate Chroma writes in the unified write path behind a check (content hash comparison against what's already in the collection, or `upsert()` with Chroma-side dedup) before calling embedding generation.
**Warning signs:** Server startup time growing noticeably after Stage 3 lands; CPU pegged at 100% for minutes after every restart.

### Pitfall 2: Mixed-quality source corpus undermines D-08's clean assumption
**What goes wrong:** `data/documents/special/` is not uniformly Traditional or Simplified — sampled files include garbled OCR output mixing English artifacts and malformed Chinese (e.g. one sampled `.ppt.txt` file: `"Mini-plastic Surgery UH - HARE / HARES PEE LIED"` followed by OCR-garbled mixed-language text) [VERIFIED: `data/documents/special/鹏程微整形年龄管理鹏程全.ppt.txt` — read this session, tail sample]. Running OpenCC over garbled OCR text won't fix or worsen the garbling (OpenCC only maps recognized Han characters), but it means D-08's normalization pass should not be assumed to produce clean output — some retrieved chunks will remain noisy regardless of Stage 4's fix, which is a pre-existing data-quality issue, not something this phase is scoped to solve.
**Why it happens:** `special_docs` corpus includes legacy OCR/video-transcript artifacts (filenames like `--02.flv.txt` suggest transcribed video content).
**How to avoid:** Don't scope-creep into "fixing" OCR quality in this phase; note it as a known limitation in D-09's observability logging (a chunk that scores low or reads garbled in logs is expected, not a fusion bug).
**Warning signs:** Retrieval observability logs (D-09) show high-scoring chunks with obviously corrupted text.

### Pitfall 3: `data/documents/general/` file-count mismatch with CONTEXT.md's framing
**What goes wrong:** CONTEXT.md's Stage 4 description says "the 848 `medical_kb_batch_*.txt` files" as if that glob pattern captures the whole ingestion target. Actual count: `data/documents/general/` has 848 files total, but only 45 of them literally match the `medical_kb_batch_*.txt` naming pattern — the remaining ~803 are individually-named files (e.g. `10岁女童急性阑尾炎发作转移性右下腹疼痛 .doc.txt`) [VERIFIED: `ls data/documents/general/ | grep -c medical_kb_batch` → 45; `ls data/documents/general/ | wc -l` → 848 — run this session]. Both sets are Simplified Chinese medical content per sampling.
**Why it happens:** The "848" figure describes the directory's total file count, not files matching that specific glob.
**How to avoid:** When implementing D-08's normalization pass and D-03's `document_folders` config fix, ingest/normalize the **entire directory** (`data/documents/general/*.txt`, all 848 files), not a `medical_kb_batch_*` glob filter — a glob-scoped implementation would silently skip ~803 files.
**Warning signs:** `scripts/rebuild_rag.py --force` reports far fewer than 848 documents ingested for the general collection.

### Pitfall 4: `get_scored_chunks()` doesn't expose the row id
**What goes wrong:** The SQL query in `SimpleIndex.get_scored_chunks()` selects only `c.content` and the bm25 score, never `c.id` [VERIFIED: `src/rag_engine.py:93-99` — read this session, `SELECT c.content, bm25(rag_chunks_fts) as score FROM rag_chunks c JOIN rag_chunks_fts f ON c.id = f.rowid WHERE c.category = ? AND rag_chunks_fts MATCH ? ORDER BY score ASC LIMIT 30`]. Any RRF/fusion code that assumes it can pull a stable ID out of this function's return value without modifying it will fail.
**Why it happens:** The function predates any need for cross-store correlation.
**How to avoid:** Per D-05, don't modify `get_scored_chunks()`'s scoring internals — but note it currently returns `List[Tuple[float, str]]` (score, content only), confirmed from the function's own `return scored_chunks` at line 126 where `scored_chunks.append((score, content))` (line 121) [VERIFIED: `src/rag_engine.py:113-126` — read this session]. Build `HybridRetriever`'s fusion on content-hash keys (Pattern 2), not row IDs, until Stage 3 lands.
**Warning signs:** `AttributeError` or `KeyError` if code assumes a 3-tuple or dict return shape from `get_scored_chunks()`.

## Code Examples

### Wiring the embedding function into both DocumentIngestor and SemanticSearch consistently

```python
# Both DocumentIngestor._init_chroma() and SemanticSearch._init_client() must use
# the SAME embedding_function instance/config, or Chroma's conflict validation
# (validate_embedding_function_conflict_on_get, chromadb/api/client.py) will raise.
# Source: chromadb==1.5.9 installed source, read this session.
from chromadb.utils import embedding_functions

def make_embedding_function(model_name: str, device: str = "cpu"):
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=model_name, device=device,
    )

# In DocumentIngestor._init_chroma():
self.collection = self.client.get_or_create_collection(
    name=self.collection_name,
    metadata={"description": "Medical documents for RAG"},
    embedding_function=make_embedding_function(self.embedding_model, "cpu"),
)

# In SemanticSearch._init_client(), the get_collection() call must be given the
# same embedding_function so query-time embedding matches ingest-time embedding:
self.collection = self.client.get_collection(
    name=self.collection_name,
    embedding_function=make_embedding_function(self.embedding_model, "cpu"),
)
```

### Latency measurement harness (for the D-02 bge-small-zh-v1.5 vs bge-m3 decision)

```python
# Run this on the target machine before locking in a default model, per D-02's
# explicit "decide by measuring actual query latency on this machine" instruction.
import time
from sentence_transformers import SentenceTransformer

sample_queries = ["肉毒桿菌術後多久可以洗臉？", "玻尿酸過敏怎麼辦？", "雷射術後保養注意事項"]

for model_name in ["BAAI/bge-small-zh-v1.5", "BAAI/bge-m3"]:
    model = SentenceTransformer(model_name, device="cpu")
    model.encode(sample_queries)  # warm-up (excludes model-load time from timing)
    start = time.perf_counter()
    for _ in range(20):
        model.encode(sample_queries)
    elapsed_ms = (time.perf_counter() - start) / 20 * 1000
    print(f"{model_name}: {elapsed_ms:.1f} ms per batch of {len(sample_queries)} queries")
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|---------------|--------|
| Chroma default embedding (bundled English-only ONNX `all-MiniLM-L6-v2`) | Explicit `embedding_function=` passed to `get_or_create_collection()` | This has been Chroma's documented pattern since well before 1.x; the dormant code in this repo simply never applied it | Chinese queries currently silently degrade to an English-tuned model if Chroma is ever actually populated without this fix — this is exactly D-01's bug. |
| chromadb 0.4.x API (the `pyproject.toml` floor) | chromadb 1.5.9 (installed) | Chroma had a major rewrite between the 0.4.x line and the 1.x line; `get_or_create_collection`'s default `embedding_function` parameter and the `Collection`/config-persistence model reflect the 1.x architecture, verified from installed source this session | Any code examples or tutorials targeting 0.4.x may reference a different (older) API shape; this document's examples are verified against the actually-installed version. |

**Deprecated/outdated:** None identified as deprecated within this phase's scope — the phase is wiring existing, current-generation libraries correctly, not migrating off something old.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | `BAAI/bge-m3`'s parameter count (~568M, cited from web search) and CPU latency figures (~31ms/query cited from one arXiv benchmark, hardware unspecified) | Standard Stack / State of the Art discussion, Code Examples latency harness | If the cited benchmark's hardware differs significantly from this project's Xeon E5-2686 v4 (36 vCPU, no GPU used for embeddings per D-02), real latency could be substantially higher or lower — this is exactly why D-02 requires an on-machine measurement before locking in a default, and the research explicitly does not substitute for that measurement. |
| A2 | `BAAI/bge-small-zh-v1.5` embedding dimension (512) and max sequence length (512 tokens), sourced via WebFetch summarizing the Hugging Face model card rather than reading the model card's config.json directly | Standard Stack, Pattern 1 | If dimension/seq-length are misreported, downstream code that hardcodes vector dimensions (unlikely needed here since Chroma infers dimension from the embedding function automatically) would be unaffected, but chunk-size tuning relative to the model's context window could be off. Low risk given Chroma auto-detects dimension. |
| A3 | Neither `BAAI/bge-small-zh-v1.5` nor `BAAI/bge-m3` weights are already cached locally (no `~/.cache/huggingface` presence check was run this session) | Common Pitfalls ("Loading model weights synchronously") | If weights are already cached, first-call latency concern is moot; if not, first use requires a network fetch (multiple hundred MB for bge-m3) which could fail in an offline/firewalled deployment — worth a `checkpoint:human-verify` before relying on this at implementation time. |
| A4 | Elasticsearch's RRF documentation is being used as the citation source for the k=60 constant and formula, rather than the original Cormack et al. 2009 TREC paper directly | Pattern 2 (RRF) | Very low risk — Elastic's documented formula and default match the widely-cited academic original; this is a well-established, non-controversial technique with no version-specific API surface to get wrong. |

## Open Questions

1. **Will `scripts/rebuild_rag.py` need modification for D-04's collection rename and D-07's shared-chunk-id write, or does it already parameterize collection names/chunking cleanly?**
   - What we know: The script exists (97 lines [VERIFIED: `wc -l scripts/rebuild_rag.py` — this session]) and CONTEXT.md says it's "reused as-is" for Stage 1 verification and Stage 3's re-ingest.
   - What's unclear: Its internals were not read in depth this session (out of the explicit file list provided); the planner should read it before writing Stage 1/Stage 3 tasks to confirm it already accepts collection-name and chunker parameters, or needs a small update.
   - Recommendation: Planner should include a task to read `scripts/rebuild_rag.py` in full before writing the Stage 1/3 plan steps that depend on it.

2. **Does book-to-skil.md's recommended BGE cross-encoder reranking step apply to this phase?**
   - What we know: book-to-skil.md's step 3 (read this session, lines 84-88) explicitly recommends RRF **followed by** a BGE cross-encoder reranker before truncating to top-k. CONTEXT.md's D-05 through D-09 only cover RRF fusion — no reranker is mentioned in any locked decision.
   - What's unclear: Whether omitting the reranker is an intentional scope-narrowing by the user (likely, since CONTEXT.md is otherwise very precise about citing book-to-skil.md) or an oversight.
   - Recommendation: Treat reranking as explicitly out of scope for this phase (not listed in Decisions or Claude's Discretion) — flag as a candidate for a follow-up phase rather than folding it in here, consistent with how CONTEXT.md's Deferred Ideas section handles other book-to-skil.md-adjacent items.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| `chromadb` | D-01–D-07 (all of Chroma wiring) | ✓ | 1.5.9 | — |
| `sentence-transformers` | D-01, D-02 (embedding function) | ✗ | latest 6.0.0 on PyPI | Must be added to `pyproject.toml` before Stage 1 work starts — no viable fallback within Chroma's bundled `SentenceTransformerEmbeddingFunction`, which hard-requires it. |
| `opencc` (PyPI `OpenCC`) | D-08 (normalization) | ✗ | latest 1.4.2 on PyPI | Must be added to `pyproject.toml`. Fallback: `opencc-python-reimplemented` (pure Python, no compiled extension) if the compiled `opencc` binding fails to install in this environment — not yet tested. |
| `torch` (CPU inference path) | D-02 (embedding model backend) | ✓ | 2.12.0+cu130 | — (already installed; CUDA available but D-02 locks embeddings to CPU) |
| GPU (CUDA) | Not required by this phase's locked decisions | ✓ (present) | NVIDIA GeForce RTX 2080 Ti, ~23GB VRAM | N/A — informational only; D-02 explicitly keeps embeddings on CPU to avoid contending with the LLM's GPU usage. |
| Network access to Hugging Face Hub (model weight download) | First-run download of `bge-small-zh-v1.5`/`bge-m3` weights | Not verified this session — no cache-presence check was run | — | If offline, pre-download weights via `huggingface-cli download` before deployment; flag as a `checkpoint:human-verify` item (Assumption A3). |

**Missing dependencies with no fallback:**
- `sentence-transformers` — required, no substitute within the chosen Chroma embedding-function pattern.

**Missing dependencies with fallback:**
- `opencc` — fallback to `opencc-python-reimplemented` if the compiled binding has install issues.

## Security Domain

`security_enforcement` is not set in `.planning/config.json` (absent = enabled per policy), so this section is included. This phase does not touch authentication, session management, or access control — `RAGEngine`/`HybridRetriever` are internal backend components with no new external-facing surface added by this phase (the existing `/api/v1/rag/*` Flask routes are pre-existing and only get collection-name-default touch-ups per the pitfall noted above, not new endpoints).

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-------------------|
| V2 Authentication | No | Not touched by this phase. |
| V3 Session Management | No | Not touched by this phase. |
| V4 Access Control | No | Not touched by this phase. |
| V5 Input Validation | Partial | Query text passed to `SemanticSearch.search(query_texts=[query], ...)` and `SimpleIndex.get_scored_chunks(q)` is free-form user chat text, already regex-filtered for Chinese-character keyword extraction in the sparse path (existing code, unchanged). Chroma's `query_texts` parameter is embedded, not interpreted as a query language, so there's no injection surface analogous to SQL — the SQLite FTS5 `MATCH` query string is already built via `" OR ".join([f'"{k}"' for k in filtered_kvs])` (existing code, unchanged by this phase), which quotes each keyword; this phase does not add new unvalidated input paths. |
| V6 Cryptography | No | Not applicable — no new secrets/crypto introduced. |
| V12 File & Resources | Partial (ingest-time only) | `data/documents/{general,special}/` are trusted local filesystem paths already read by the existing `_initial_ingest()` pipeline (not new to this phase); Stage 3's unified chunking pass reads the same trusted paths. No new file-upload or path-traversal surface is introduced by this phase — the pre-existing `/api/v1/rag/ingest` endpoint's `file_path` handling is untouched (out of scope). |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|----------------------|
| Data poisoning via untrusted source documents (a malicious/corrupted `.txt` file in `data/documents/`) affecting retrieval | Tampering | Out of scope for this phase — documents are locally-curated clinic content, not user-uploaded at ingest time via this path; no new mitigation introduced or required. |
| Sensitive data (patient identifiers, pricing) leaking into retrieved chunks and then into LLM answers | Information Disclosure | Already mitigated by the existing price-redaction `re.sub` post-processing in `_get_context()` (unchanged by D-05, explicitly preserved per CONTEXT.md) — this phase's fusion output passes through the same redaction step before reaching the LLM prompt. |

## Sources

### Primary (HIGH confidence)
- `.venv/lib/python3.12/site-packages/chromadb/api/client.py` (installed chromadb 1.5.9) — `get_or_create_collection` signature, read this session
- `.venv/lib/python3.12/site-packages/chromadb/utils/embedding_functions/sentence_transformer_embedding_function.py` (installed chromadb 1.5.9) — `SentenceTransformerEmbeddingFunction` full source, read this session
- `src/rag_engine.py`, `src/rag/ingest.py`, `src/rag/search.py`, `src/api/routes/rag.py`, `src/rag/query.py`, `src/agent/hermes_core.py`, `src/data_loader.py`, `config/settings.py`, `config/ingest_config.json`, `pyproject.toml` — all read directly this session
- PyPI JSON API (`https://pypi.org/pypi/<package>/json`) — version/release-history verification for `chromadb`, `sentence-transformers`, `opencc`/`OpenCC`, `zhconv`, `hanziconv`, `opencc-python-reimplemented`, queried this session
- `data/documents/general/medical_kb_batch_1.txt`, `data/documents/general/10岁女童急性阑尾炎发作转移性右下腹疼痛 .doc.txt`, `data/documents/special/鹏程微整形年龄管理鹏程全.ppt.txt` — sampled directly this session to confirm Simplified/mixed source-language claims

### Secondary (MEDIUM confidence)
- Elastic RRF documentation (`elastic.co/guide/en/elasticsearch/reference/8.19/rrf.html`) — RRF formula and k=60 default, via WebSearch this session
- BYVoid/OpenCC GitHub (`github.com/BYVoid/OpenCC`, `data/config/s2twp.json`) — `s2twp` config purpose and Python usage example, via WebSearch this session
- Hugging Face model cards for `BAAI/bge-m3` and `BAAI/bge-small-zh-v1.5` — dimensions, max sequence length, sentence-transformers compatibility, via WebFetch this session (model card content, not directly-read config.json)

### Tertiary (LOW confidence)
- arXiv paper cited by WebSearch for bge-m3's ~31ms CPU latency figure — hardware specifics not confirmed, flagged in Assumptions Log A1; must be superseded by an on-machine measurement per D-02.
- bge-m3 parameter count (~568M) — WebSearch-derived, not read from an authoritative config.json; flagged in Assumptions Log A1.

## Metadata

**Confidence breakdown:**
- Standard stack (chromadb/sentence-transformers/opencc APIs and versions): HIGH — installed-package source read directly, PyPI registry cross-checked
- Architecture (integration points, write-path idempotency risk, collection-name coupling): HIGH — all claims verified against in-repo source read this session
- Pitfalls: HIGH for code-level findings (file/line citations with verbatim quotes); MEDIUM for corpus-quality observations (based on small samples, not exhaustive scan of 1,726 files)
- Embedding model latency/sizing (bge-small-zh-v1.5 vs bge-m3): MEDIUM — sourced from web search/model cards, explicitly requires on-machine measurement per D-02 before being treated as settled

**Research date:** 2026-08-25
**Valid until:** 30 days (stack is stable; re-verify chromadb/sentence-transformers versions if implementation slips past ~2026-09-25, as chromadb has shown a fast release cadence — 130 releases in 3.5 years)
