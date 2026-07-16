# Phase 04: Integration of Medical Knowledge Graph - Research

This document outlines the technical research for integrating the structured medical knowledge graph into the `DrtoolboxLocalServer` codebase.

---

## 1. Source Data Analysis (`medical.json`)
The source file is located at `chatbot-base-on-Knowledge-Graph/data/medical.json`.
It is a JSON Lines (JSONL) file where each line represents a disease entity with its attributes and relationships.
Key keys per record:
- `name`: Name of the disease (e.g., "肺氣腫").
- `desc`: Brief description.
- `cause`: Cause of the disease.
- `prevent`: Prevention methods.
- `cure_lasttime`: Duration of treatment.
- `cure_way`: Treatment methods.
- `cured_prob`: Cure probability.
- `easy_get`: Susceptible demographic.
- `symptom`: List of symptom entities (relationship: `has_symptom`).
- `acompany`: List of accompanying diseases/complications (relationship: `acompany_with`).
- `common_drug`: List of common drugs (relationship: `common_drug`).
- `recommand_drug`: List of recommended drugs (relationship: `recommand_drug`).
- `check`: List of checkups/tests (relationship: `need_check`).
- `do_eat`: List of foods recommended to eat (relationship: `do_eat`).
- `no_eat`: List of foods to avoid (relationship: `no_eat`).
- `recommand_eat`: List of specific food recipes (relationship: `recommand_eat`).

---

## 2. Relational Schema in SQLite
Instead of running a full Neo4j graph database, we store nodes and edges directly in the existing SQLite database (`clinic.db`) under `/data/db/clinic.db`.

### 2.1 Table Schema
```sql
CREATE TABLE IF NOT EXISTS medical_nodes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    label TEXT NOT NULL -- 'Disease', 'Symptom', 'Drug', 'Check', 'Food'
);

CREATE TABLE IF NOT EXISTS medical_edges (
    source_id INTEGER NOT NULL,
    target_id INTEGER NOT NULL,
    relation TEXT NOT NULL, -- 'has_symptom', 'recommand_drug', 'no_eat', etc.
    PRIMARY KEY (source_id, target_id, relation),
    FOREIGN KEY (source_id) REFERENCES medical_nodes(id) ON DELETE CASCADE,
    FOREIGN KEY (target_id) REFERENCES medical_nodes(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_nodes_name ON medical_nodes(name);
CREATE INDEX IF NOT EXISTS idx_edges_source ON medical_edges(source_id);
```

### 2.2 Attribute Storage
Since SQLite doesn't natively support property graphs, we can store disease attributes (like `desc`, `cause`, `prevent`) directly as properties on the `medical_nodes` table or in a separate `disease_details` table:
```sql
CREATE TABLE IF NOT EXISTS disease_details (
    node_id INTEGER PRIMARY KEY,
    description TEXT,
    cause TEXT,
    prevent TEXT,
    cure_lasttime TEXT,
    cured_prob TEXT,
    FOREIGN KEY (node_id) REFERENCES medical_nodes(id) ON DELETE CASCADE
);
```

---

## 3. NLP Extraction Strategy
We will replace `chatbot-base-on-Knowledge-Graph`'s BiLSTM-CRF and TextCNN with a prompt-engineered local LLM query.

### 3.1 Local LLM Entity & Intent Extraction
We will construct a structured extraction prompt:
```text
System: You are an NLP extraction agent. Given a medical question in Chinese, extract:
1. Medical entities (Diseases, Symptoms, Drugs, Checks, Foods)
2. Question category (symptom, drug, check, food, cause, prevent)
Return your answer strictly in JSON format.
```
This is robust, leverages the existing Llama-3/Gemma GPU backend via `src/llm_server.py`, and doesn't require any PyTorch/TensorFlow weight loading.

---

## 4. Integration with RAGEngine
We will add `GraphRAGEngine` inside `src/rag/` (e.g., `src/rag/graph_rag_engine.py`) and hook it into `src/rag_engine.py`.

In `src/rag_engine.py`:
- Initialize `GraphRAGEngine`.
- In `query_integrated`, invoke `GraphRAGEngine.query(question)`.
- Merge the results with the current SQL and PageIndex results.
- Apply strict pricing regex masks (`[請致電診所確認]`) and safety warnings before final LLM completion.

---

## 5. Verification Plan
- **Migration Test**: Run `scripts/migrate_medical_graph.py` and verify `medical_nodes` contains >40,000 records.
- **Query Test**: Perform relational queries (e.g. finding symptoms of "感冒") and verify outputs.
- **Integration Test**: Query `/message` API with medical questions and assert Traditional Chinese responses with no pricing leakage.
