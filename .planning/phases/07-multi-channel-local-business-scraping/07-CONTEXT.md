# Phase 7: Multi-Channel 10km Local Business Scraping & Multi-Tier Outreach - Context

**Gathered:** 2026-07-23
**Status:** Ready for planning
**Source:** User Request & Technical Architecture Integration

<domain>
## Phase Boundary

This phase expands the B2B lead discovery pipeline to target non-clinic local businesses within a 10km radius of Zhiyan Aesthetic Clinic (緻妍診所). Utilizing Firecrawl deep web scraping techniques from `doctor-toolbox-post`, the system extracts Emails, FB Page URLs, FB Messenger URLs, and Latest FB Post URLs for local target entities (gyms, yoga studios, tech firms, wedding photography, etc.). Data is ingested into an expanded `b2b_leads` table in `clinic.db` to support a 3-tier outreach cascade (Email -> FB Messenger -> FB Post Comment) with LINE VIP binding tracking and Dashboard visualization.

</domain>

<decisions>
## Implementation Decisions

### 1. Database Schema Extension (`b2b_leads`)
- Add columns: `fb_page_url`, `fb_messenger_url`, `latest_post_url`, `category`, `outreach_channel`.
- Ensure backward compatibility with Phase 6 `openoutreach_bridge.py`.

### 2. Local Business Firecrawl Scraper (`scripts/local_b2b_scraper.py`)
- Call local Firecrawl container (`http://127.0.0.1:3002`) or web scraper to extract official website Markdown, Email addresses, and FB links for 10km targets.
- Auto-generate company IDs, UTM tokens, and default preferred outreach channels (`email` -> `messenger` -> `post_comment`).

### 3. Multi-Channel Outreach Dispatch Strategy
- **Tier 1 (Email)**: Send HTML email with CID embedded poster and LINE VIP link (zero-price compliance).
- **Tier 2 (FB Messenger)**: Auto-format Messenger outreach message with LINE VIP URL for leads lacking Email.
- **Tier 3 (FB Post Comment)**: Fallback comment invitation on the target's latest FB post URL if Messenger is disabled or fails.

### 4. Web Dashboard Visualization Update
- Update `tab-analytics` B2B panel in `dashboard.html` & `dashboard.js` to display channel breakdown (Email / Messenger / Post Comment) alongside LINE VIP binding counts.

</decisions>

<canonical_refs>
## Canonical References

- `scripts/openoutreach_bridge.py` — Existing B2B lead table schema & Zero-price sanitizer
- `src/api/routes/webhook.py` — LINE VIP `b2b_` UTM token auto-linking logic
- `/tmp/doctor-toolbox-post/firecrawl_scraper.py` — Firecrawl deep scraping reference

</canonical_refs>

<specifics>
## Specific Ideas

- Focus on non-clinic local businesses within 10km (hospitals/clinics excluded).
- Maintain AGENTS.md strict zero-price guardrails across all 3 outreach channels.

</specifics>

<deferred>
## Deferred Ideas

- Automated FB account rotation with proxies (Keep to local single account / standard SMTP for Tier 1 & 2).

</deferred>

---

*Phase: 07-multi-channel-local-business-scraping*
*Context gathered: 2026-07-23*
