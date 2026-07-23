# Phase 7 Plan 1: Multi-Channel 10km Local Business Mining & Multi-Tier Outreach

## Overview
Expand `b2b_leads` schema to support multi-channel fields (FB Page, Messenger, Latest Post), build `scripts/local_b2b_scraper.py` for Firecrawl 10km mining, and implement the 3-tier outreach cascade (Email -> Messenger -> FB Comment) with dashboard UI visualization.

## Execution Tasks

### Task 1: Database Schema Expansion (`scripts/openoutreach_bridge.py`)
- Update `init_b2b_tables()` in `scripts/openoutreach_bridge.py` to add `fb_page_url`, `fb_messenger_url`, `latest_post_url`, `category`, and `outreach_channel` columns via `PRAGMA table_info` checks.
- Add helper method `add_full_lead()` to insert multi-channel lead details.
- **Files Modified**: `scripts/openoutreach_bridge.py`

### Task 2: 10km Local Business Firecrawl Scraper (`scripts/local_b2b_scraper.py`)
- Implement `scripts/local_b2b_scraper.py` targeting 10km local non-clinic businesses (gyms, yoga, tech, wedding).
- Integrate Firecrawl API (`http://127.0.0.1:3002`) to extract Email, FB Page URL, Messenger URL, and Latest Post URL, auto-ingesting into `b2b_leads`.
- **Files Modified**: `scripts/local_b2b_scraper.py`

### Task 3: 3-Tier Multi-Channel Outreach Dispatch Engine
- Extend `OpenOutreachBridge` with `dispatch_multi_channel_outreach(company_id)` implementing:
  1. Priority 1: Email (with `AGENTS.md` pricing defense & LINE VIP link).
  2. Priority 2: FB Messenger (with LINE VIP link).
  3. Priority 3: FB Post Comment (with LINE VIP link).
- Add endpoint `POST /api/dashboard/analytics/b2b/dispatch_channel` in `src/api/routes/dashboard.py`.
- **Files Modified**: `scripts/openoutreach_bridge.py`, `src/api/routes/dashboard.py`

### Task 4: Dashboard UI Multi-Channel Breakdown (`dashboard.html` & `dashboard.js`)
- Update B2B panel in `dashboard.html` to show multi-channel badges (`📧 Email`, `💬 Messenger`, `💬 Comment`).
- Update `dashboard.js` `loadAnalytics()` and lead addition form to support category selection and multi-channel status display.
- **Files Modified**: `src/templates/dashboard.html`, `src/static/js/dashboard.js`

### Task 5: Testing & Integration Verification
- Write Pytest unit tests in `tests/test_local_b2b_scraper.py` verifying schema expansion, multi-channel lead ingestion, and 3-tier dispatch logic.
- **Files Modified**: `tests/test_local_b2b_scraper.py`
