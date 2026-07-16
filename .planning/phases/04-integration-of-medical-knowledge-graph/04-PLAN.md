# Phase 04: Integration of Medical Knowledge Graph - Plan

- **Phase:** 04
- **Name:** Integration of Medical Knowledge Graph
- **Goal:** Ingest 300k+ relationships of medical knowledge graph into SQLite and implement Graph-RAG reasoning in Hermes.

---

## 1. Threat Model
- **Threat 1: Prompt Injection / Brand Leakage.** User query attempts to force LLM to reveal it is running on "Drtoolbox" or "樹義美醫".
  - *Mitigation:* System prompt overrides and output validation enforce "緻妍診所智慧醫療助理小妍" persona.
- **Threat 2: Pricing Leakage.** Medical graph data contains reference drug prices or diagnostic package costs that are outdated.
  - *Mitigation:* Explicit regex price-scrubbing filter applied unconditionally to RAG context before it reaches LLM.

---

## 2. Tasks

### Milestone 1: Database Setup & Migration
- [ ] **Task 1.1: Create SQLite Schema Migration Script**
  - Create `scripts/migrate_medical_graph.py` which defines tables: `medical_nodes`, `medical_edges`, and `disease_details`.
  - Implement JSONL parsing logic to read from `chatbot-base-on-Knowledge-Graph/data/medical.json` in chunks.
  - Apply Transaction batching to insert 44k nodes and 300k relations efficiently (target time: < 30 seconds).
- [ ] **Task 1.2: Run Ingestion Command**
  - Execute `python scripts/migrate_medical_graph.py`.
  - Validate counts: `medical_nodes` > 40,000, `medical_edges` > 250,000.

### Milestone 2: Graph-RAG Retrieval Core
- [ ] **Task 2.1: Implement Graph-RAG Engine**
  - Create `src/rag/graph_rag_engine.py` with `GraphRAGEngine` class.
  - Implement LLM extraction helper to parse user query into entities.
  - Implement SQLite multi-hop retriever (e.g., retrieving related symptoms, drugs, foods).
- [ ] **Task 2.2: Hook Graph-RAG to RAGEngine**
  - Modify `src/rag_engine.py` to import `GraphRAGEngine`.
  - Integrate Graph-RAG context into `query_integrated`.
  - Verify that the strict regex filters apply to Graph-RAG retrieved outputs.

### Milestone 3: End-to-End Verification
- [ ] **Task 3.1: Write Integration Tests**
  - Write test cases in `tests/test_graph_rag.py` to query medical terms (e.g. "感冒") and assert retrieval of symptoms/drugs.
  - Verify that if a query requests price, it returns the standard warning message.
- [ ] **Task 3.2: Verify API Endpoint**
  - Start local flask server and test `/message` or `/api/v1/messages/send` with medical intent queries.

---

## 3. Definition of Done
- Ingestion script completes successfully without memory overload.
- Multi-hop query retrieves medical relationships in less than 100ms.
- LLM outputs responses in Traditional Chinese only, adhering to the "小妍" brand rules and redacting all prices.
