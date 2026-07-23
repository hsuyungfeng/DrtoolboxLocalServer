# Phase 7 Technical Research: Multi-Channel Local Business Mining & Multi-Tier Outreach

## 1. Schema Expansion for Multi-Channel Leads
- Extended `b2b_leads` schema:
  ```sql
  ALTER TABLE b2b_leads ADD COLUMN fb_page_url TEXT;
  ALTER TABLE b2b_leads ADD COLUMN fb_messenger_url TEXT;
  ALTER TABLE b2b_leads ADD COLUMN latest_post_url TEXT;
  ALTER TABLE b2b_leads ADD COLUMN category TEXT;
  ALTER TABLE b2b_leads ADD COLUMN outreach_channel TEXT;
  ```
- Priority channel determination algorithm:
  - If `contact_email` present -> `email`
  - Else if `fb_messenger_url` present -> `messenger`
  - Else if `latest_post_url` present -> `post_comment`

## 2. Local 10km Business Mining Scraper (`scripts/local_b2b_scraper.py`)
- Interfaces with local Firecrawl (`http://127.0.0.1:3002`) or requests parser to extract Email and FB links from company websites.
- Ingests structured leads into SQLite `clinic.db` `b2b_leads`.

## 3. Multi-Tier Outreach Dispatch Engine
- **Tier 1 Email**: Leverages `OpenOutreachBridge.send_outreach_email()` with `AGENTS.md` pricing sanitizer.
- **Tier 2 Messenger**: Formats Messenger template with `b2b_` LINE VIP link.
- **Tier 3 Comment**: Formats public post comment template with LINE VIP link.

## 4. Web Dashboard Multi-Channel Analytics UI
- Extends `/api/dashboard/analytics/b2b` API response with `channel_breakdown` (email count, messenger count, comment count).
- Displays multi-channel tags in `dashboard.html` B2B lead list.
