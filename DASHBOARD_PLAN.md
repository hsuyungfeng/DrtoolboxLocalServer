# Dual-Site RAG Ingestion Dashboard Plan

## Overview
Create a dashboard with two separate ingestion interfaces for the dual-collection RAG system:
1. **General Medical Site** - For general medical documents, research papers, clinical guidelines
2. **Clinic-Specific Site** - For clinic protocols, patient records, internal procedures

## Architecture

### Frontend Pages
```
/dashboard
├── /general-medical
│   ├── Document Upload Interface
│   ├── Collection Stats (general_medical_docs)
│   ├── Ingestion History
│   └── Query Testing Panel
│
└── /clinic-specific
    ├── Document Upload Interface
    ├── Collection Stats (clinic_specific_docs)
    ├── Ingestion History
    └── Query Testing Panel
```

### API Endpoints (Already Implemented)
```
POST /api/v1/rag/ingest
  - Body: { "file", "collection": "general_medical" | "clinic_specific" }
  - Returns: { "status", "chunks", "collection" }

POST /api/v1/rag/query
  - Body: { "prompt", "collection": "general_medical" | "clinic_specific" | "both" }
  - Returns: { "answer", "citations", "confidence" }

GET /api/v1/rag/collection?collection=general_medical
  - Returns: { "count", "documents", "stats" }
```

## Implementation Tasks

### Task 1: Backend Enhancement
- [ ] Add collection-specific ingest endpoints
- [ ] Add collection stats endpoint (/api/v1/rag/stats?collection=X)
- [ ] Add ingestion history tracking
- [ ] Add document deletion endpoint for each collection

### Task 2: Frontend - General Medical Site
- [ ] Create `/dashboard/general-medical` page
- [ ] Implement drag-drop file upload
- [ ] Show collection stats (3 documents, file sizes, ingestion dates)
- [ ] Add search/query testing panel
- [ ] Display ingestion history

### Task 3: Frontend - Clinic-Specific Site
- [ ] Create `/dashboard/clinic-specific` page
- [ ] Implement drag-drop file upload
- [ ] Show collection stats (3 documents, file sizes, ingestion dates)
- [ ] Add search/query testing panel
- [ ] Display ingestion history

### Task 4: Shared Dashboard Components
- [ ] Navigation between sites
- [ ] Unified search (query both collections)
- [ ] Collection comparison view
- [ ] Admin settings (chunk size, overlap, etc.)

## Database Schema (Optional - for ingestion history)
```sql
CREATE TABLE ingestion_history (
  id INTEGER PRIMARY KEY,
  collection TEXT,
  filename TEXT,
  file_size INTEGER,
  chunks_created INTEGER,
  ingested_at TIMESTAMP,
  status TEXT  -- 'success', 'failed'
);
```

## Configuration
Update `config/ingest_config.json`:
```json
{
  "chroma": {
    "path": "data/rag/chroma_new/",
    "collections": {
      "general_medical": {
        "name": "general_medical_docs",
        "description": "General Medical Knowledge Base",
        "icon": "📚",
        "color": "#4CAF50"
      },
      "clinic_specific": {
        "name": "clinic_specific_docs",
        "description": "Clinic-Specific Protocols",
        "icon": "🏥",
        "color": "#2196F3"
      }
    }
  }
}
```

## Current Status
- ✅ Dual collections implemented and working
- ✅ API endpoints support collection routing
- ✅ Semantic search operational
- ⏳ Dashboard frontend needs creation
- ⏳ Collection management UI needed

## Priority Implementation Order
1. **Phase 1** (Quick): Basic upload pages with collection selection
2. **Phase 2** (Medium): Collection stats display and ingestion history
3. **Phase 3** (Enhanced): Advanced features like document deletion, analytics

## Notes
- Both collections use Chroma persistence at `data/rag/chroma_new/`
- Current collections have 3 documents each (small for testing)
- Ready to ingest larger datasets once UI is complete
- LLM integration waiting for server connection
