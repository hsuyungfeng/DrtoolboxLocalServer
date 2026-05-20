# Phase 3: Web Dashboard & Feedback Loop - Research

## Objective
Research and design a premium Web Dashboard for clinic staff to view, search, edit, and export JSONL log data to fuel the training feedback loop.

## Technical Approach
1. **Frontend Architecture**:
   - We will use pure HTML, Vanilla CSS, and JavaScript. No heavy frontend framework is strictly necessary since it's a single dashboard page.
   - The CSS will implement a premium **Glassmorphism Dark Mode** aesthetic. We will use Inter or Outfit fonts, smooth gradients, and subtle hover animations for a responsive, high-quality feel.
2. **Backend API for Dashboard**:
   - `src/api/routes/dashboard.py`: A new blueprint to serve the JSONL data to the frontend.
   - Endpoints needed:
     - `GET /api/dashboard/logs`: Returns recent interaction logs.
     - `POST /api/dashboard/logs/<log_id>/correct`: Allows staff to submit a correction to the LLM's response, marking it as a verified training pair.
     - `GET /api/dashboard/export`: Downloads the corrected JSONL data.
3. **Data Mutation**:
   - The `LoggerService` from Phase 2 will be updated to support appending "corrections" to the existing logs or maintaining a separate `verified_training_data.jsonl`.

## Risks & Mitigations
- **Risk**: Reading large JSONL files blocking the Flask server.
  - **Mitigation**: Read the tail of the files or use pagination on the backend.
- **Risk**: Unpolished UI discouraging staff from doing data corrections.
  - **Mitigation**: Invest heavily in the aesthetic and micro-animations to make the curation process feel premium and fast.
