# Concerns

## Technical Debt & Performance
- **Local LLM Inference**: Running a model (Qwen via llama-qwen) locally on GPU is resource-intensive. VRAM overflow, slow token generation, and concurrent request handling are major performance risks.
- **PageIndex Tree Building**: Parsing large clinic documents into trees might be slow. Optimization or asynchronous processing is required.

## Security
- **HIS Integration**: Connecting the Hermes Agent to the local HIS database requires strict read-only permissions and input validation to prevent SQL injections or data exposure.
- **Data Privacy**: Storing patient conversations in `/data` necessitates anonymization and secure access controls (PII protection).

## Fragility
- Transitioning away from vector databases to pure reasoning RAG means accuracy is highly dependent on the reasoning capabilities of the local LLM. Prompt engineering and tree structures must be heavily optimized.
