# Phase 1: Foundation — Context

**Gathered:** 2026-05-06  
**Status:** Ready for execution  

---

<domain>
## Phase Boundary

Establish local LLM inference and RAG pipeline for medical document Q&A.

**Deliverables:**
- llama.cpp serving Qwen 3.6 on 2080Ti with <200ms latency
- RAG ingestion pipeline (PDF, Word, text documents)
- Flask API for RAG queries with streaming responses
- Source document citations in all responses
- GPU memory monitoring and 24h stability

</domain>

---

<decisions>
## Implementation Decisions

### LLM Inference
- **D-01**: Model: Qwen 3.6 with Q8_0 quantization
  - Target: ~250-300ms latency, ~10GB VRAM
  - Avoids OOM, acceptable for clinic-scale (<3s requirement)

- **D-02**: Output strategy: Streaming (token-by-token)
  - User sees response building in real-time
  - Better perceived latency, prevents "waiting" feeling
  - Fits <3s overall response time target

- **D-03**: Concurrency model: Dynamic batching based on queue depth
  - Start with batch_size=1, increase to 2-4 if queue builds
  - Flexible scaling without guaranteed VRAM overrun
  - Requires queue monitoring implementation

### RAG Architecture
- **D-04**: Search method: Semantic-only (vector similarity via Chroma)
  - Using existing Chroma instance (already initialized, 34MB)
  - Trade-off: Excellent conceptual matching, may miss exact terms
  - Future optimization: hybrid search if relevance drops below 0.7

- **D-05**: Document chunking: Small chunks (256-512 tokens)
  - Precise retrieval, easier source citation
  - More vectors to manage, but Chroma can handle this

- **D-06**: Vector DB: Keep existing Chroma as-is
  - No re-initialization or migration
  - Fast Phase 1 start, minimal setup overhead

### Document Ingestion
- **D-07**: Format handling: Library-based (PyPDF2, python-docx)
  - Simple, low dependencies
  - Acceptable for clinic documents (may not handle complex formatting)
  - Trade-off: No cloud service dependency, local-first

### API & Integration
- **D-08**: Framework: Flask (synchronous)
  - Lightweight, simple implementation
  - Adequate for clinic-scale concurrency
  - Pairs well with dynamic batching and streaming

- **D-09**: Source citation: Full document + section tracking
  - Store: filename, section heading, page number, ingestion timestamp
  - Supports audit trail and medical accountability
  - Overhead: minimal (few fields per chunk)

### GPU Memory & Stability
- **D-10**: Memory monitoring: nvidia-smi polling + pynvml library
  - Every 30 seconds, track VRAM usage
  - Programmatic alerts if usage exceeds 18GB

- **D-11**: Overflow prevention: Hard token limit + queue timeout
  - max_tokens=1024 to prevent runaway generation
  - Request queue with 30s timeout, drop stale requests
  - Streaming allows immediate stop if VRAM spikes

- **D-12**: Daily restart: Auto-restart llama.cpp at 2 AM
  - Safety mechanism for 24h operation
  - Low-traffic window for clinic

</decisions>

---

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Project Context
- `.planning/PROJECT.md` — Project vision, key decisions, 2080Ti constraints
- `.planning/REQUIREMENTS.md` — RAG-01 through RAG-04, LLM-01 through LLM-04 requirement specs
- `.planning/ROADMAP.md` §Phase 1 — Phase 1 objectives, success criteria, deliverables

### Implementation Guides (to be created)
- `01-LLAMA_SETUP.md` — llama.cpp installation, Qwen 3.6 quantization, Q8_0 configs
- `01-RAG_PIPELINE.md` — Chroma configuration, document chunking, semantic search
- `01-API_SERVER.md` — Flask setup, streaming endpoint design, error handling

</canonical_refs>

---

<code_context>
## Existing Code Insights

### Reusable Assets
- **Chroma vector DB**: Already initialized at `data/rag/chroma/` — use existing instance, no re-init needed
- **Medical SQLite DB**: `data/local_db/medical.db` — query schema before design document ingestion flow
- **Audio recording**: `data/recordings/` exists — Phase 1 focused on text, but infrastructure present for future voice I/O

### Established Patterns
- **Data directory structure**: `/data/{local_db,rag,recordings}/` — follow this pattern for Phase 1 outputs
- **SQLite integration**: clinic already using SQLite for medical data — use same DB driver for consistency

</code_context>

---

<specifics>
## Specific Ideas

- **Clinic-specific documents**: User mentioned "add other with clinic specially" — Phase 1 should support uploading clinic-specific medical docs (protocols, guidelines, case templates already in `data/rag/case_templates.db`)
- **Quick validation**: After setup, test RAG with 5-10 clinic documents to validate relevance before full rollout

</specifics>

---

<deferred>
## Deferred Ideas

- **Hybrid BM25 + semantic search**: Reconsidered and deferred. Start with semantic-only; upgrade to hybrid in Phase 5 if relevance metrics show need.
- **Cloud service fallback for PDF parsing**: Deferred to v2. Local libraries sufficient for clinic document quality.
- **Gemma 4 model support**: Deferred to Phase 5. Focus Phase 1 on Qwen 3.6 stability.
- **Advanced analytics on retrieval patterns**: Deferred to Phase 4 (Hermes agent analysis). Phase 1 focuses on core RAG functionality.

</deferred>

---

*Phase: 01-foundation*  
*Context gathered: 2026-05-06*  
*Ready for planning and execution*
