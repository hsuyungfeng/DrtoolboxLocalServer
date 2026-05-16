# Tech Stack

## Languages & Runtime
- **Python 3.9+**: Primary language for the backend, Hermes agent, and data processing.
- **Node.js/Bash**: Assumed for minor scripts or hermes-desktop (Electron/Vite).

## Frameworks & Core Libraries
- **Backend**: Flask or FastAPI (for webhooks, API endpoints).
- **RAG Engine**: [VectifyAI/PageIndex](https://github.com/VectifyAI/PageIndex) for reasoning-based, vectorless RAG.
- **Local Inference**: `llama.cpp` for local serving of Gemma 4 27B.
- **Orchestration**: Hermes Agent framework.
- **Package Manager**: `uv` (as evidenced by `uv.lock` and `pyproject.toml`).

## Configuration
- Environment variables managed via `.env`.
- Project configuration stored in `pyproject.toml`.
