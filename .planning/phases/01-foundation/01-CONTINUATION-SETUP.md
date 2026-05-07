# Phase 1 Continuation: Dual-Collection RAG Setup

**Date**: 2026-05-07  
**Status**: Infrastructure complete, ready for document ingestion  
**Commit**: `ad6e55e` — Dual-collection RAG implementation

---

## What's New: Two-Part Knowledge Base

Your RAG system now supports **two separate, searchable collections**:

### 1. **general_medical** — Common Disease References
- Location: `data/rag/general_docs/`
- Purpose: Medical treatment guidelines, disease information, standard protocols
- Access: Drop PDFs/Word docs here, run ingest script

### 2. **clinic_specific** — Your Clinic's Internal Knowledge
- Location: `data/rag/clinic_docs/`
- Purpose: Your clinic's own protocols, staff procedures, patient notes
- Access: Drop PDFs/Word docs here, run ingest script

---

## How It Works

### Query Behavior
Every query **searches both collections** and merges results ranked by relevance:
```
Patient asks: "What is diabetes treatment?"
  → Searches general_medical (standard treatments)
  → Searches clinic_specific (your clinic's protocol)
  → Returns top 5 combined, ranked by similarity
  → Each result labeled with source collection
```

### API Interface

**Query with merged results (default):**
```bash
curl -X POST http://localhost:5000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{"prompt":"What is diabetes treatment?","collection":"both"}'
```

**Query only clinic docs:**
```bash
curl -X POST http://localhost:5000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Our protocols","collection":"clinic_specific"}'
```

**Query only general knowledge:**
```bash
curl -X POST http://localhost:5000/api/v1/rag/query \
  -H "Content-Type: application/json" \
  -d '{"prompt":"Standard treatment","collection":"general_medical"}'
```

**Ingest to clinic collection:**
```bash
curl -X POST http://localhost:5000/api/v1/rag/ingest \
  -F "file=@clinic_protocol.pdf" \
  -F "collection=clinic_specific"
```

---

## Quick Start: Ingest Your Documents

### Option 1: One-Command Batch Ingest
```bash
bash scripts/ingest_all.sh
```

This script:
1. Scans both `data/rag/general_docs/` and `data/rag/clinic_docs/`
2. Ingests all PDFs, Word docs, and text files found
3. Routes each file to the correct ChromaDB collection
4. Reports chunks ingested per collection

### Option 2: Manual Ingest
```bash
# General medical documents
curl -F "file=@treatment_guide.pdf" \
  -F "collection=general_medical" \
  http://localhost:5000/api/v1/rag/ingest

# Clinic-specific documents
curl -F "file=@clinic_workflow.docx" \
  -F "collection=clinic_specific" \
  http://localhost:5000/api/v1/rag/ingest
```

---

## Files Changed (Commit ad6e55e)

| File | Change |
|------|--------|
| `config/ingest_config.json` | Added `collections` dict, `document_folders`, `default_collection` |
| `src/rag/ingest.py` | Fixed typo bug (boundry → boundary) on line 273 |
| `src/rag/search.py` | Added `search_dual()` function for merged queries |
| `src/rag/query.py` | Extended `QueryAnswer` with optional `clinic_search` parameter |
| `src/api/routes/rag.py` | Updated API routes to accept `collection` parameter |
| `scripts/ingest_all.sh` | New: One-command batch ingestion script |
| `data/rag/general_docs/` | New folder for general medical documents |
| `data/rag/clinic_docs/` | New folder for clinic-specific documents |

---

## Technical Details

### Dual Collection Architecture
- **Single ChromaDB instance** (`data/rag/chroma_new/`) contains **two named collections**
- Each collection has its own HNSW vector index
- Documents share embedding model but maintain separate semantic spaces

### Query Merging Logic
```python
def search_dual(query, general_search, clinic_search, top_k=5):
    results_general = general_search.search(query, top_k=5)
    results_clinic = clinic_search.search(query, top_k=5)
    
    # Tag source collection
    for r in results_general: r.metadata['_collection'] = 'general_medical'
    for r in results_clinic: r.metadata['_collection'] = 'clinic_specific'
    
    # Merge and re-rank by similarity (clinic docs prioritized on ties)
    merged = sorted(results_general + results_clinic, 
                   key=lambda x: (x.similarity, x.metadata['_collection']=='clinic_specific'),
                   reverse=True)
    
    return merged[:top_k]  # Top 5 from merged
```

### Config Structure
```json
{
  "chroma": {
    "path": "data/rag/chroma_new/",
    "collections": {
      "general_medical": "general_medical",
      "clinic_specific": "clinic_specific"
    },
    "default_collection": "general_medical"
  },
  "document_folders": {
    "general_medical": "data/rag/general_docs/",
    "clinic_specific": "data/rag/clinic_docs/"
  }
}
```

---

## Next Steps: Prepare Your Documents

### For General Medical Docs
Drop standard treatment guides, disease references, diagnostic protocols into:
```
data/rag/general_docs/
├── diabetes_treatment.pdf
├── hypertension_guidelines.docx
└── diagnostic_flowcharts.txt
```

### For Clinic-Specific Docs
Drop your clinic's internal docs into:
```
data/rag/clinic_docs/
├── clinic_workflow.pdf
├── staff_procedures.docx
├── patient_intake_form.txt
└── local_protocols.pdf
```

Then run:
```bash
bash scripts/ingest_all.sh
```

---

## Verification Checklist

- [x] Dual collections created in ChromaDB
- [x] search_dual() function implemented
- [x] API routes updated with collection parameter
- [x] ingest_all.sh script ready
- [x] Document folders created
- [x] Configuration updated
- [ ] **YOUR TURN**: Place sample documents and run ingestion
- [ ] Test merged query returns results from both collections
- [ ] Test targeted queries (clinic_specific only, general_medical only)

---

## Questions Before Proceeding?

1. **Document formatting**: Do you have PDFs, Word docs, or plain text files ready?
2. **Ingestion strategy**: Should ingest_all.sh skip already-ingested files (by hash), or always re-ingest?
3. **Testing**: Want to test with sample documents first, or go live with real clinic data?

**Ready?** Drop your documents and run `bash scripts/ingest_all.sh`!

---

*Phase 1 continuation complete. Next: Phase 2 (HIS + LINE integration) after documents are indexed.*
