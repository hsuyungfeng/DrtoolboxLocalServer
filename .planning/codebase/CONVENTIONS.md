# Conventions

## Code Style
- **Python**: PEP-8 compliance, likely enforced via tools managed by `uv`.
- **Types**: Type hinting is highly recommended for backend logic and agent functions.

## Naming
- Python files: `snake_case.py`
- Directories: `lowercase/`

## Error Handling
- Use structured logging to ensure all interactions and failures are tracked in `/data`.
- Fallbacks for LLM timeouts or GPU OOM errors when interacting with `llama.cpp` and local inferences.
