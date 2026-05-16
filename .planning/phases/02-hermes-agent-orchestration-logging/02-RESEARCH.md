# Phase 2: Hermes Agent Orchestration & Logging - Research

## Objective
Research integration of Hermes agent for intelligent routing between the clinic's special data and general medical data, along with JSON interaction logging.

## Technical Approach
1. **Hermes Agent Integration**:
   - `hermes-agent` will serve as the orchestrator. It will receive user queries, analyze intent, and invoke the appropriate tool (either `query_special_data` or `query_general_data` via the `RAGEngine` established in Phase 1).
   - This effectively creates a Router agent pattern.
2. **LINE/Web Chat Integration**:
   - We need endpoints in our Flask API to receive incoming messages and pass them to the Hermes agent.
3. **JSON Logging**:
   - Every interaction must be logged for future model fine-tuning.
   - We'll create a `LoggerService` in `src/services/logger_service.py` that serializes the conversation (User Prompt, LLM Response, Tools Used) and appends it to JSONL files in the `/data/logs` directory.

## Risks & Mitigations
- **Risk**: Hermes failing to strictly adhere to the tools (hallucination).
  - **Mitigation**: Use strict system prompts defining exactly when to use which tool.
- **Risk**: Concurrent writes to JSONL logs.
  - **Mitigation**: Use threading locks or rotate files safely when writing logs.
