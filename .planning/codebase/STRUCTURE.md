# Directory Structure

- `/src`: Main application source code (backend, agent logic, routing).
- `/data`: Centralized storage for data collection, conversation logs, human corrections, and JSONL training datasets.
- `/documents`: Raw clinic manuals, FAQs, and rules to be parsed into PageIndex trees.
- `/scripts`: Utility scripts (e.g., `ingest_all_collections.py` for indexing documents).
- `/config`: System configurations.
- `/cron`: Scheduled jobs (e.g., nightly CRM analysis via Hermes-desktop).
- `.planning`: Project tracking and GSD state.
