# Phase 3: Web Dashboard & Feedback Loop - Plan

## 1. Backend Data Editor & Export API
- **Description:** Create the `dashboard_bp` in Flask to serve log data to the frontend, accept corrections, and allow downloading the JSONL.
- **Files Modified:** `src/api/routes/dashboard.py`, `src/services/logger_service.py`, `src/api/app.py`
- **Dependencies:** None
- **Acceptance Criteria:** `GET /api/dashboard/logs` returns recent logs. `POST /api/dashboard/logs/<id>/correct` saves a correction. `GET /api/dashboard/export` returns a downloadable file.

## 2. Implement Design System (CSS)
- **Description:** Create the core CSS framework for the dashboard using Vanilla CSS. Implement a premium Dark Mode with Glassmorphism, using `Outfit` or `Inter` from Google Fonts, smooth gradients, and vibrant accent colors.
- **Files Modified:** `static/css/index.css`
- **Dependencies:** None
- **Acceptance Criteria:** The CSS file provides utility classes for glass panels, buttons with hover micro-animations, and typography.

## 3. Build the Dashboard UI
- **Description:** Build `index.html` and the associated Javascript (`static/js/dashboard.js`). It must fetch the data from the API and render it beautifully. Staff must be able to click on a log, view the interaction, and type a correction.
- **Files Modified:** `templates/dashboard.html`, `static/js/dashboard.js`
- **Dependencies:** 1, 2
- **Acceptance Criteria:** The UI is responsive, looks extremely premium, and successfully connects to the backend API to render and correct logs.

## 4. Verification & Testing
- **Description:** Verify the feedback loop end-to-end.
- **Files Modified:** `tests/test_dashboard_api.py`
- **Dependencies:** 3
- **Acceptance Criteria:** Tests ensure that applying a correction to a log correctly updates the `verified_training_data` store.
