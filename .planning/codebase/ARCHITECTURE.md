# Architecture

## Core Patterns
- **Reasoning-based RAG**: Instead of chunking/vector similarity (Chroma/FAISS removed), the system builds a hierarchical tree of clinic documents using `PageIndex` and navigates it via LLM reasoning.
- **Agent Orchestration**: `Hermes Agent` serves as the primary dispatcher, managing context, routing messages, and triggering the PageIndex engine.
- **Data-Centric Loop**: All interactions are logged to `/data` to capture high-quality QA pairs for future fine-tuning.

## Data Flow
1. Patient sends a message via LINE/Web Chat.
2. Webhook triggers Flask/FastAPI backend.
3. `Hermes Agent` processes the message, querying local HIS if dynamic context is needed.
4. If document knowledge is required, `PageIndex` performs a tree search over the clinic manuals using local `Gemma 4 27B` (via `llama.cpp`).
5. Response is returned to the user, and the interaction + feedback is appended to `/data` in JSONL format.
