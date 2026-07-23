# Phase 6 Technical Research: OpenOutreach Integration & Local B2B Outreach

## 1. OpenOutreach Architecture & Local Integration
- **OpenOutreach Engine**: Python 3.12+ Django & Docker-based B2B lead discovery and active learning email generator.
- **ICP Filtering**: Targets local business entities within 3-5km radius (Corporate Welfare Committees, HR, VIP Business Partners).
- **Bridge Architecture**: Create `scripts/openoutreach_bridge.py` to sync discovered leads into local SQLite `clinic.db` (`b2b_leads` table).

## 2. LINE Linking & Tracking Mechanism
- **UTM Tracking**: Generate custom LINE onboarding URLs: `https://line.me/R/ti/p/@zhiyan?utm_source=b2b_email&company_id={id}`.
- **Automated VIP Tagging**: `line_linking.py` captures `company_id` upon first chat event and labels patient record in `clinic.db` as `b2b_vip`.

## 3. Strict Compliance Guardrails
- **AGENTS.md Pricing Rule**: OpenOutreach LLM system prompt explicitly instructs zero hardcoded pricing ($ amounts). All CTAs direct to "Corporate VIP Consultation" or "Request Partnership Brochure".

## 4. BI Analytics Integration
- Extend `tab-analytics` in `dashboard.html` with a B2B Funnel Widget:
  - Outreach Sent (Total Leads Contacted)
  - Email Open / Click Rate
  - LINE VIP Linked Count
  - HIS Appointments Converted
