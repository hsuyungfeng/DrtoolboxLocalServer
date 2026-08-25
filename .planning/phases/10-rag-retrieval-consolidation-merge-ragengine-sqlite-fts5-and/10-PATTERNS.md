# Phase 10: RAG Retrieval Consolidation - Pattern Map

**Mapped:** 2026-08-25
**Files analyzed:** 9
**Analogs found:** 9 / 9 (all modify-in-place or have a direct sibling analog; no file has zero precedent)

## File Classification

| New/Modified File | Role | Data Flow | Closest Analog | Match Quality |
|-------------------|------|-----------|-----------------|---------------|
| `src/rag/ingest.py` (`_init_chroma`, D-01/D-02) | service (ingest) | CRUD (write) | `src/rag/search.py` `_init_client()` (sibling Chroma client init) | exact (same module family) |
| `src/rag/search.py` (`_init_client`, `search`, D-01/D-02) | service (query) | request-response | itself — self-modification; secondary analog `src/rag/ingest.py::_init_chroma` | exact |
| `src/rag/hybrid.py` (NEW — `HybridRetriever`, RRF, D-05/D-06) | service (fusion) | request-response, transform | `src/rag_engine.py::SimpleIndex.get_scored_chunks()` (scoring/query shape) + `src/rag/search.py::SemanticSearch.search()` (dense query shape) | role-match (new file, composes two existing services) |
| `src/rag_engine.py::_get_context()` (swap-in point, D-05) | controller-ish orchestrator (already exists) | request-response | itself, lines ~577-596 (in-place edit) | exact |
| `src/rag/ingest.py::chunk_text()` reused for `SimpleIndex.add_document()` (D-07) | utility (chunker) | transform | `src/rag/ingest.py::chunk_text()` (lines 321-407) itself, called from a new site in `rag_engine.py` | exact |
| `src/rag_engine.py::SimpleIndex.add_document()` (rewritten write path, D-07) | model/repository (SQLite write) | CRUD (write) | itself, current version lines 39-67 | exact (in-place rewrite) |
| `src/rag/normalize.py` (NEW — OpenCC wrapper, D-08) | utility (text transform) | transform | `src/rag/ingest.py::parse_document()` (pre-chunk transform step it plugs into, lines 157-198) | role-match |
| `src/api/routes/rag.py` (`get_ingestor`, `get_query_answer`, `load_config` defaults, D-04 coupling fix) | route/config | request-response | itself, lines 28-121 (in-place edit) | exact |
| `config/ingest_config.json` (D-02/D-03/D-04) | config | — | itself (in-place edit) | exact |
| `scripts/rebuild_rag.py` (verify parameterization for D-04/D-07) | utility (CLI) | batch | not yet read — planner should read this file in full before writing Stage 1/3 tasks (per RESEARCH.md Open Question 1) | unknown — flagged below |

## Pattern Assignments

### `src/rag/ingest.py::_init_chroma()` (D-01, D-02) — service, CRUD-write

**Analog:** itself, current broken version + `src/rag/search.py::_init_client()` as the sibling pattern for how the *other* Chroma-touching class in this codebase structures client init.

**Current buggy version** (`src/rag/ingest.py:126-155`):
```python
def _init_chroma(self) -> bool:
    """Initialize Chroma client."""
    if not CHROMA_AVAILABLE:
        logger.error("chromadb not installed")
        return False
    try:
        os.makedirs(self.chroma_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=self.chroma_dir,
            settings=Settings(anonymized_telemetry=False, allow_reset=True)
        )
        # BUG: no embedding_function passed — falls back to Chroma's
        # bundled English-only all-MiniLM-L6-v2 ONNX default
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"description": "Medical documents for RAG"}
        )
        logger.info(f"Chroma collection ready: {self.collection_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Chroma: {e}")
        return False
```

**Fix pattern (from RESEARCH.md, verified against installed chromadb==1.5.9 source):**
```python
from chromadb.utils import embedding_functions

def make_embedding_function(model_name: str, device: str = "cpu"):
    return embedding_functions.SentenceTransformerEmbeddingFunction(
        model_name=model_name, device=device,
    )

# inside _init_chroma():
self.collection = self.client.get_or_create_collection(
    name=self.collection_name,
    metadata={"description": "Medical documents for RAG"},
    embedding_function=make_embedding_function(self.embedding_model, "cpu"),
)
```
Keep the same `try/except Exception as e: logger.error(...); return False` shape — this is the established error-handling convention in this file and must not change.

---

### `src/rag/search.py::_init_client()` (D-01, D-02) — service, request-response

**Analog:** itself (lines 85-116); must use the **same** `embedding_function` construction as `ingest.py` or Chroma's `validate_embedding_function_conflict_on_get` raises.

**Current version** (`src/rag/search.py:85-116`):
```python
def _init_client(self) -> bool:
    if not CHROMA_AVAILABLE:
        logger.error("chromadb not installed")
        return False
    try:
        os.makedirs(self.chroma_dir, exist_ok=True)
        self.client = chromadb.PersistentClient(
            path=self.chroma_dir,
            settings=Settings(anonymized_telemetry=False, allow_reset=True)
        )
        try:
            self.collection = self.client.get_collection(name=self.collection_name)
        except Exception as e:
            logger.warning(f"Collection '{self.collection_name}' not found: {e}")
            return False
        logger.info(f"Connected to collection: {self.collection_name}")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize Chroma client: {e}")
        return False
```

**Fix:** pass the same `embedding_function=make_embedding_function(...)` into `get_collection()`. Note the nested try/except (outer for client creation, inner for collection lookup with a `warning` not `error` log level, returning `False` without raising) — preserve this two-tier error handling exactly; it is the existing convention distinguishing "client init failed" from "collection doesn't exist yet."

**Query/search pattern to reuse as-is** (`src/rag/search.py:118-179`) — `HybridRetriever` should call this method, not reimplement it:
```python
def search(self, query, top_k=None, where=None, where_document=None, include_scores=True) -> List[SearchResult]:
    if self.collection is None:
        if not self._init_client():
            raise RuntimeError(f"Collection '{self.collection_name}' not found. Use DocumentIngestor to ingest documents first.")
    if top_k is None:
        top_k = self.default_top_k
    try:
        results = self.collection.query(
            query_texts=[query], n_results=top_k,
            include=['documents', 'metadatas', 'distances'],
        )
        search_results = []
        if results.get('documents') and results['documents'][0]:
            for i, doc in enumerate(results['documents'][0]):
                distance = results['distances'][0][i]
                metadata = results['metadatas'][0][i]
                doc_id = results['ids'][0][i]
                search_results.append(SearchResult(text=doc, id=doc_id, score=0.0, distance=distance, metadata=metadata))
        search_results.sort(key=lambda x: x.distance)
        # ... similarity calculated after this point
```
Note: `SemanticSearch.search()` raises `RuntimeError` on missing collection (not a silent empty-list return) — `HybridRetriever` (D-06) MUST wrap its call to `.search()` in try/except and catch this `RuntimeError` too, not just generic exceptions, to satisfy the "never hard-fail the live chatbot" requirement.

---

### `src/rag/hybrid.py` (NEW) — `HybridRetriever` + RRF, service/transform

**No direct analog exists** (this is genuinely new code) — compose from two read patterns:

1. **Sparse side pattern** — `src/rag_engine.py::SimpleIndex.get_scored_chunks()` (lines 69-126): returns `List[Tuple[float, str]]` = `(score, content)`, already sorted ascending by bm25 internally but re-sorted descending by caller. No chunk id available (RESEARCH.md Pitfall 4) — must use content-hash as correlation key until Stage 3.

2. **Dense side pattern** — `src/rag/search.py::SemanticSearch.search()` (above): returns `List[SearchResult]` with `.text`, `.id`, `.distance`, `.similarity` property.

3. **Error-handling convention to match** — every DB/LLM call in `rag_engine.py` is wrapped `try/except Exception as e: logger.error(f"..."); ` with a safe fallback value (see `SimpleIndex.get_scored_chunks()` lines 123-126: catches, logs, falls through to `return scored_chunks` which may be empty). `HybridRetriever`'s Chroma call must follow this exact shape — catch, log, fall back to sparse-only results, never raise up into `_get_context()`.

**RRF fusion implementation** (from RESEARCH.md Pattern 2, ready to use verbatim):
```python
import hashlib
from typing import List, Tuple

def _key(text: str) -> str:
    """Best-effort correlation key pre-Stage-3; becomes chunk_id post-Stage-3."""
    return hashlib.md5(text.strip().encode("utf-8")).hexdigest()

def reciprocal_rank_fusion(
    sparse_ranked: List[Tuple[float, str]],   # (score, content) from get_scored_chunks(), sorted desc
    dense_ranked: List[str],                  # content strings from SemanticSearch.search(), sorted by similarity desc
    k: int = 60,
) -> List[str]:
    fused_scores: dict = {}
    content_by_key: dict = {}
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

**Suggested class shape** (composes the above, matches `SimpleIndex`'s constructor style of taking `category`/index refs directly rather than config objects):
```python
class HybridRetriever:
    def __init__(self, sparse_index, dense_search, k: int = 60):
        self.sparse_index = sparse_index   # SimpleIndex instance (special_index or general_index)
        self.dense_search = dense_search   # SemanticSearch instance for matching collection
        self.k = k

    def get_scored_chunks(self, question: str) -> List[str]:
        sparse_ranked = self.sparse_index.get_scored_chunks(question)
        sparse_ranked.sort(reverse=True, key=lambda x: x[0])
        try:
            dense_results = self.dense_search.search(question, top_k=10)
            dense_ranked = [r.text for r in dense_results]
        except Exception as e:
            logger.error(f"HybridRetriever: Chroma dense search failed, falling back to sparse-only: {e}")
            return [content for _, content in sparse_ranked]  # D-06 fallback
        return reciprocal_rank_fusion(sparse_ranked, dense_ranked, k=self.k)
```

---

### `src/rag_engine.py::_get_context()` swap-in point (D-05) — orchestrator, request-response

**Analog:** itself, exact current lines (`src/rag_engine.py:577-596`):
```python
# 3. SimpleIndex Context Lookup
logger.info(f"[_get_context] Querying SimpleIndex (route: {route})...")
if route == "special":
    rag_scored_chunks = self.special_index.get_scored_chunks(question)
else:
    rag_scored_chunks = self.general_index.get_scored_chunks(question)

rag_scored_chunks.sort(reverse=True, key=lambda x: x[0])
top_chunks = []
seen = set()
for score, chunk in rag_scored_chunks:
    if chunk not in seen:
        seen.add(chunk)
        text = re.sub(r'\$\s*\d+(?:,\d+)*', '[請致電確認]', chunk)
        text = re.sub(r'\d+(?:,\d+)*\s*[元塊]', '[請致電確認]', text)
        top_chunks.append(text)
    if len(top_chunks) >= 4: break
rag_context = "\n\n".join(top_chunks)
if not rag_context: rag_context = "無相關原始文本片段。"
logger.info(f"[_get_context] SimpleIndex done. Context length: {len(rag_context)}")
```

**Swap plan:** replace `self.special_index.get_scored_chunks(question)` / `self.general_index.get_scored_chunks(question)` calls with `self.hybrid_retriever_special.get_scored_chunks(question)` / `self.hybrid_retriever_general.get_scored_chunks(question)` — the fused result is already `List[str]` (post-RRF), so the subsequent dedup-loop and price-redaction `re.sub` block (unchanged per D-05/D-09) needs a minor adjustment: iterate `for chunk in fused_chunks:` instead of `for score, chunk in rag_scored_chunks:` since RRF output has no per-chunk score to unpack (or keep score if `HybridRetriever` returns `(fused_score, content)` tuples for D-09 logging — recommended, since D-09 wants "fused scores were actually used" logged).
**Keep unchanged:** the top-4 cap (`if len(top_chunks) >= 4: break`), the `seen` dedup set, both `re.sub` price-redaction lines, and the `無相關原始文本片段。` empty-fallback string.
**`HybridRetriever` instances constructed in `RAGEngine.__init__()`** (`src/rag_engine.py:128-140`), analogous to how `self.special_index = SimpleIndex(...)` / `self.general_index = SimpleIndex(...)` are constructed today at lines 136-137 — add `self.hybrid_special = HybridRetriever(self.special_index, SemanticSearch(collection_name="special", ...))` and the `general` equivalent in the same constructor block.

---

### `src/rag_engine.py::SimpleIndex.add_document()` rewrite (D-07) — model/repository, CRUD-write

**Current version** (`src/rag_engine.py:39-67`) — fixed-stride chunking to replace:
```python
def add_document(self, doc):
    doc_id = doc.get('id', '')
    content = doc.get('content', '')
    if not content:
        return
    with db_write_lock:
        try:
            conn = sqlite3.connect(self.db_path, timeout=30.0)
            cursor = conn.cursor()
            cursor.execute("DELETE FROM rag_chunks WHERE doc_id = ? AND category = ?", (doc_id, self.category))
            chunk_index = 0
            for i in range(0, len(content), 400):
                chunk_text = content[i:i+600]
                cursor.execute("""
                    INSERT INTO rag_chunks (doc_id, category, chunk_index, content)
                    VALUES (?, ?, ?, ?)
                """, (doc_id, self.category, chunk_index, chunk_text))
                chunk_index += 1
            conn.commit()
            conn.close()
        except Exception as e:
            logger.error(f"Failed to add document chunks to SQLite: {e}")
```

**Chunker to reuse** — `DocumentIngestor.chunk_text()` (`src/rag/ingest.py:321-407`), sentence/paragraph-boundary-aware, section-detecting, already generates a stable `chunk_id` via `_generate_chunk_id()` (`src/rag/ingest.py:409-413`, `f"chunk_{Path(source).stem}_{index}_{hash_suffix}"`). Per D-07, `SimpleIndex.add_document()` must call this same chunker (import `DocumentIngestor` or extract `chunk_text`/`_generate_chunk_id` to a shared module) and write `chunk_id` into a new/existing column on `rag_chunks` so Chroma and SQLite share the identical `chunk_id` per chunk. Keep the surrounding `with db_write_lock: try/except Exception as e: logger.error(...)` shape unchanged — this is the established write-path pattern.
**Note:** `rag_chunks` table schema currently has no `chunk_id` column (only `doc_id`, `category`, `chunk_index`, `content`) — planner should check `_init_db()` (not yet read; search `CREATE TABLE rag_chunks` in `rag_engine.py`) for whether a migration/ALTER TABLE is needed, or whether `chunk_index` combined with `doc_id` already suffices as long as the *same* chunker produces the same boundaries deterministically.

---

### `src/rag/normalize.py` (NEW) — OpenCC wrapper, utility/transform (D-08)

**No direct analog** — pure new utility module. Plug-in point is `DocumentIngestor.parse_document()` (`src/rag/ingest.py:157-198`), which already returns raw `text` per format (`.txt`, `.pdf`, `.docx`, `.pptx`, `.json`) before chunking — insert normalization as a post-parse, pre-chunk step:
```python
from opencc import OpenCC
_converter = OpenCC('s2twp')

def normalize_to_traditional(text: str) -> str:
    return _converter.convert(text)
```
**Integration pattern:** call `normalize_to_traditional(text)` at the end of `parse_document()` (or immediately after, at the `ingest()` call site around `src/rag/ingest.py:415+`) before passing text into `chunk_text()`. Match the existing per-format `try/except` structure in `parse_document()` (lines 181-198) — wrap the OpenCC call similarly so a normalization failure degrades to raw text with a logged warning, not a hard ingest failure.

---

### `src/api/routes/rag.py` collection-name defaults (D-04 coupling fix) — route/config, request-response

**Current hardcoded defaults** (`src/api/routes/rag.py:28-121`) that must be updated in lockstep with D-04's collection rename:
```python
def load_config():
    global _config
    if not _config:
        ...
        except Exception as e:
            _config = {
                "chroma": {
                    "path": "data/rag/chroma/",
                    "collections": {
                        "general_medical": "general_medical",   # <- rename to "general": "general"
                        "clinic_specific": "clinic_specific",   # <- rename to "special": "special"
                    },
                    "default_collection": "general_medical",   # <- rename to "general"
                },
                "chunking": {"chunk_size": 512, "chunk_overlap": 50},
            }
    return _config

def get_ingestor(collection: str = "general_medical") -> DocumentIngestor:   # <- default "general"
    ...

def get_query_answer(collection: str = "both") -> QueryAnswer:
    ...
    if collection == "both":
        general_search = get_ingestor("general_medical").collection   # <- "general"
        clinic_search = get_ingestor("clinic_specific").collection    # <- "special"
        ...
        general = SemanticSearch(chroma_dir=chroma_path, collection_name="general_medical", default_top_k=5)  # <- "general"
        clinic = SemanticSearch(chroma_dir=chroma_path, collection_name="clinic_specific", default_top_k=5)   # <- "special"
```
**Pattern:** every literal `"general_medical"` / `"clinic_specific"` string in this file (function default params, the in-code fallback config dict, and the `SemanticSearch`/`DocumentIngestor` construction calls) must become `"general"` / `"special"` together — grep the whole file for both strings before editing, don't rely on `config/ingest_config.json` alone since this fallback dict is used when the config file fails to load.

---

### `config/ingest_config.json` (D-02, D-03, D-04) — config file

**Current** (full file, 47 lines, read above) — required edits:
```json
{
  "chroma": {
    "collections": {
      "general_medical": "general_medical",   →  "general": "general",
      "clinic_specific": "clinic_specific"    →  "special": "special"
    },
    "default_collection": "general_medical"   →  "general"
  },
  "document_folders": {
    "general_medical": "data/rag/general_docs/",  →  "general": "data/documents/general/",
    "clinic_specific": "data/rag/clinic_docs/"     →  "special": "data/documents/special/"
  },
  "embedding": {
    "model": "sentence-transformers/all-MiniLM-L6-v2",  →  "BAAI/bge-small-zh-v1.5" (or bge-m3 per latency test)
    "device": "cpu"   // unchanged, already correct per D-02
  }
}
```
Note the `document_folders` and `chroma.collections` keys must be renamed consistently — if `document_folders` keeps using `general_medical`/`clinic_specific` as dict keys while `chroma.collections` renames to `general`/`special`, any code keying off `document_folders` by collection name breaks. Check `scripts/rebuild_rag.py`'s usage of `document_folders` keys before finalizing this rename (see Open Question below).

---

## Shared Patterns

### Defensive try/except with logged fallback (applies to `hybrid.py`, `ingest.py`, `search.py`, `normalize.py`)
**Source:** `src/rag_engine.py::SimpleIndex.get_scored_chunks()` lines 123-126, `SimpleIndex.add_document()` lines 66-67, `src/rag/search.py::_init_client()` lines 107-116.
```python
try:
    ...
except Exception as e:
    logger.error(f"<Component>: <what failed>: {e}")
    # fall through to a safe default (empty list / False / unchanged input)
```
**Apply to:** `HybridRetriever`'s Chroma call (D-06 non-negotiable), `normalize.py`'s OpenCC call, any new Chroma init code in `ingest.py`/`search.py`.

### Module-level singleton / lazy-init pattern for expensive resources
**Source:** `src/api/routes/rag.py` `_ingestors: Dict[str, DocumentIngestor] = {}` / `_query_answers: Dict[str, QueryAnswer] = {}` module-level caches (lines 22-24), and `RAGEngine.__init__()` constructing `self.special_index` / `self.general_index` once at engine construction (`src/rag_engine.py:136-137`).
**Apply to:** the `sentence-transformers` embedding model, which RESEARCH.md flags must be loaded once and reused (Chroma's own `SentenceTransformerEmbeddingFunction.models` class-dict already caches per `model_name`, so simply constructing the embedding function inside `RAGEngine.__init__()` / `DocumentIngestor.__init__()` rather than per-request is sufficient — do not add a second caching layer).

### Post-processing price-redaction regex (unchanged, must still run after fusion)
**Source:** `src/rag_engine.py:590-591` (rag_context) and `:610-616` (graph_context, more elaborate version).
```python
text = re.sub(r'\$\s*\d+(?:,\d+)*', '[請致電確認]', chunk)
text = re.sub(r'\d+(?:,\d+)*\s*[元塊]', '[請致電確認]', text)
```
**Apply to:** whatever `HybridRetriever`/RRF returns, before it's joined into `rag_context` — same location in `_get_context()`, unchanged per D-05.

## No Analog Found

| File | Role | Data Flow | Reason |
|------|------|-----------|--------|
| `src/rag/hybrid.py` | service | transform | Genuinely new composition; built from two existing services' patterns (see Pattern Assignments above), not copied from a single analog. |
| `src/rag/normalize.py` | utility | transform | Genuinely new; no existing text-normalization utility module in the codebase — plugs into `DocumentIngestor.parse_document()`'s existing per-format structure. |

## Open Items for Planner

1. **`scripts/rebuild_rag.py` (97 lines) was not read this session** — RESEARCH.md flags this explicitly as an Open Question. Planner must read it in full before writing Stage 1 (verify Chroma population) and Stage 3 (re-ingest) plan steps, to confirm it already parameterizes collection names / `document_folders` keys cleanly against the D-03/D-04 renames, or needs its own edit.
2. **`rag_chunks` table schema** (`_init_db()` in `src/rag_engine.py`, not read this session) — confirm whether a `chunk_id` column already exists or needs an `ALTER TABLE` for D-07's shared-chunk-id write path.
3. **`src/rag/query.py`** (imported by `src/api/routes/rag.py` as `QueryAnswer`) was referenced but not read — likely out of scope (D-05's swap point is `RAGEngine._get_context()`, not the `/api/v1/rag/query` HTTP path), but worth a quick planner check if Stage 2 work is expected to touch it too.

## Metadata

**Analog search scope:** `src/rag_engine.py`, `src/rag/ingest.py`, `src/rag/search.py`, `src/api/routes/rag.py`, `config/ingest_config.json`, `src/agent/hermes_core.py` (all read this session, per file list in RESEARCH.md's canonical refs)
**Files scanned:** 6 read in full/targeted sections; `scripts/rebuild_rag.py` and `src/rag/query.py` deliberately deferred to planner (flagged above)
**Pattern extraction date:** 2026-08-25
