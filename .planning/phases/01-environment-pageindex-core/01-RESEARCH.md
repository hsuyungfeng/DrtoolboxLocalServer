# Phase 1: Environment & PageIndex Core - Research

## Objective
Research how to implement PageIndex and data segregation for local Gemma 4 27B inference.

## Technical Approach
1. **PageIndex Setup**:
   - `pageindex` uses hierarchical trees instead of vector similarity.
   - It requires a local LLM integration for reasoning over the nodes.
   - `llama.cpp` will be used as the inference engine (via its python binding or HTTP server) to serve Gemma 4 27B.
2. **Data Segregation**:
   - We need to initialize two separate PageIndex instances or a routing mechanism to handle "Clinic Special Data" and "General Medical Data".
   - Clinic Special Data requires loading from `/media/hsu/软件/行銷圖文檔案整理`.

## Risks & Mitigations
- **Risk**: Inference timeout with a large model like Gemma 4 27B.
  - **Mitigation**: Offload layers to GPU if available; ensure PageIndex reasoning steps use concise prompts.
- **Risk**: File parsing errors from marketing documents.
  - **Mitigation**: Implement robust OCR/text extraction fallbacks for non-standard PDFs/images in the special data folder.
