# Architecture

## Core Patterns
- **N-gram Match RAG (SimpleIndex)**: Instead of vector similarity or complex trees, the system uses a high-performance N-gram character matching algorithm. It chunks clinic documents and scores them based on character overlap and sequential N-gram matches from the query.
- **Agent Orchestration**: `HermesRouter` serves as the primary dispatcher, managing context, routing messages to either 'special' (clinic-specific) or 'general' (medical) knowledge bases.
- **Data-Centric Loop**: All interactions are logged to `/data` to capture high-quality QA pairs for future fine-tuning.

## Data Flow
1. Patient sends a message via LINE/Web Chat.
2. Webhook triggers Flask backend.
3. `HermesRouter` processes the message, querying local HIS (SQLite) for clinic hours if applicable.
4. If document knowledge is required, `SimpleIndex` performs an N-gram keyword search over the cached document chunks using local `Qwen` (via `llama-qwen`).
5. Response is returned to the user, and the interaction is appended to `/data` in JSONL format.
