# Phase 6 Plan 1: OpenOutreach Integration & Local B2B Outreach Pipeline

## Overview
Implement the local B2B outreach infrastructure using `eracle/OpenOutreach`, connecting lead discovery with LINE VIP tagging, strict pricing rules, and dashboard BI analytics.

## Execution Tasks

### Task 1: B2B Lead Database Schema & OpenOutreach Bridge Setup
- Create `b2b_leads` table in `clinic.db` to store corporate lead status, company name, contact email, UTM token, and conversion status.
- Implement `scripts/openoutreach_bridge.py` to interface with OpenOutreach lead outputs, sync contacts, and enforce AGENTS.md zero-price compliance on outbound email prompts.
- **Files Modified**: `scripts/openoutreach_bridge.py`, `src/db/` (if schema migration needed)

### Task 2: LINE VIP Tagging & B2B Attribution (`line_linking.py`)
- Update LINE link handling in `src/agent/` or `src/api/routes/webhook.py` to parse B2B UTM parameters upon LINE QR code scanning.
- Automatically assign `b2b_vip` tag and target company ID to patient profiles in `clinic.db` `patients` table.
- **Files Modified**: `src/api/routes/webhook.py`, `src/services/patient_service.py`

### Task 3: B2B Corporate Outreach ROI Dashboard Widget
- Add "🏢 企業地推轉化榜 (Corporate Outreach ROI)" widget to `src/templates/dashboard.html` (`tab-analytics`).
- Implement API endpoint `/api/dashboard/analytics/b2b` in `src/api/routes/dashboard.py` returning outreach metrics (sent, opened, LINE linked, booked).
- **Files Modified**: `src/templates/dashboard.html`, `src/static/js/dashboard.js`, `src/api/routes/dashboard.py`

### Task 4: Unit Testing & Integration Verification
- Write unit tests verifying zero price leak in generated OpenOutreach email templates.
- Test B2B UTM tracking flow and dashboard analytics endpoint response.
- **Files Modified**: `tests/test_openoutreach_bridge.py`
