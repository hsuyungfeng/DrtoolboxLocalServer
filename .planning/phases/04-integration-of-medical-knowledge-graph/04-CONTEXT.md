# Phase 04: Integration of Medical Knowledge Graph - Context

**Gathered:** 2026-07-16
**Status:** Ready for planning
**Source:** PRD Express Path (improveplan.md)

<domain>
## Phase Boundary

This phase delivers the integration of the structured medical knowledge graph from `chatbot-base-on-Knowledge-Graph` into the existing `DrtoolboxLocalServer` (緻妍診所智慧醫療助理「小妍」系統). The scope includes:
- Migrating the Neo4j-based graph data (from `chatbot-base-on-Knowledge-Graph/data/medical.json` containing 44k nodes and 300k relationships) into the local SQLite database.
- Upgrading the Hermes agent's retrieval capabilities to query this new Graph database (Graph-RAG) in addition to the existing HIS database and PageIndex SimpleIndex RAG.
- Replacing the obsolete TensorFlow 1.x models (BiLSTM-CRF & TextCNN) with local LLM zero-shot extraction or standard Python utilities.
- Adapting the retrieved context to fully comply with Zhiyan Clinic's brand requirements and strict pricing safety rules.

</domain>

<decisions>
## Implementation Decisions

### Database Migration
- **Locked Decision:** Do not install or run a full Neo4j graph database. Instead, convert the graph data to standard relational SQLite tables inside `clinic.db` (or a separate `medical_knowledge.db`).
- **Locked Decision:** Create two tables: `medical_nodes` (id, name, label) and `medical_edges` (source_id, target_id, relation).
- **Locked Decision:** Write a Python migration script (`scripts/migrate_medical_graph.py`) to parse `chatbot-base-on-Knowledge-Graph/data/medical.json` and populate the SQLite tables.

### NLP & Retrieval
- **Locked Decision:** Replace the legacy BiLSTM-CRF (NER) and TextCNN (classification) with LLM-based zero-shot extraction.
- **Locked Decision:** Implement a Graph-RAG retriever (`src/rag/graph_rag_engine.py`) that extracts medical entities from user questions, performs multi-hop SQL queries to find related symptoms/drugs/checks/foods, and translates them into natural language snippets.
- **Locked Decision:** Integrate the new Graph-RAG retriever into `src/rag_engine.py` under the hybrid query method.

### Safety & Compliance
- **Locked Decision:** Apply the clinic's strict pricing redaction rules to the Graph-RAG output using regex filters (redacting prices and returning the clinic contact prompt).
- **Locked Decision:** Adhere to `AGENTS.md` guidelines: response in Traditional Chinese, persona as "緻妍診所智慧醫療助理小妍", and no mention of "樹義美醫" or "Drtoolbox".

### the agent's Discretion
- The exact wording of prompt messages used for LLM-based entity extraction.
- Optimization of SQL queries for multi-hop graph retrieval.
- Folder placement for new schema definitions (if any).

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Clinic Agents and Rules
- `AGENTS.md` — Brand persona guidelines and strict pricing security rules.
- `src/agent/hermes_core.py` — Core Hermes agent implementation.
- `src/agent/hermes_router.py` — Simulates routing logic for local LLM.

### Ingestion and RAG
- `src/rag_engine.py` — Current RAGEngine combining SQLite and PageIndex SimpleIndex.
- `improveplan.md` — Full integration architectural plan.
- `chatbot-base-on-Knowledge-Graph/data/medical.json` — Source graph JSON.

</canonical_refs>

<specifics>
## Specific Ideas
- Graph relationships to support: `has_symptom` (disease -> symptom), `recommand_drug` (disease -> drug), `no_eat` (disease -> food/avoid), `acompany_with` (disease -> complication), `need_check` (disease -> test).
- Safe pricing message fallback: "目前無法確認該活動的時效與具體內容，為避免提供錯誤資訊，建議您致電診所向專人諮詢以獲取最準確的報價喔！"

</specifics>

<deferred>
## Deferred Ideas
- Multi-user collaboration graphs or web graph visualizers (out of scope for local server).

</deferred>

---

*Phase: 04-integration-of-medical-knowledge-graph*
*Context gathered: 2026-07-16 via PRD Express Path*
