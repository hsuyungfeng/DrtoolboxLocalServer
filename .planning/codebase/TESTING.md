# Testing

## Frameworks
- **Pytest**: Detected `.pytest_cache` indicates `pytest` is the primary testing framework.

## Structure
- Tests are likely located in a `tests/` directory or alongside components.
- Mocking: External API calls (LINE, HIS) and heavy LLM inferences (llama.cpp) should be mocked in unit tests to ensure fast CI/CD execution.

## Coverage Goals
- Focus on testing the data collection pipeline, ensuring JSONL exports are valid.
- Test Hermes Agent routing logic.
