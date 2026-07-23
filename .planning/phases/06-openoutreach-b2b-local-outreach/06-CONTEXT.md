# Phase 6: OpenOutreach B2B Local Outreach & LINE Integration - Context

**Gathered:** 2026-07-23
**Status:** Ready for planning
**Source:** User Request & Technical Survey Analysis

<domain>
## Phase Boundary

This phase integrates `eracle/OpenOutreach` agentic email discovery engine into `DrtoolboxLocalServer` for Zhiyan Aesthetic Clinic (緻妍診所)'s local B2B outreach (corporate wellness, local business partnerships, corporate VIP discounts within 10km radius). It bridges OpenOutreach leads with LINE VIP tagging (`line_linking.py`), enforces strict pricing security rules (`AGENTS.md`), and presents B2B funnel tracking in the Web Dashboard (`tab-analytics`).

</domain>

<decisions>
## Implementation Decisions

### 1. Lead Discovery & Local ICP (Ideal Customer Profile)
- Target local corporates, HR/Welfare committees, yoga studios, gyms, and wedding photo studios within 3-5 km.
- Integrate OpenOutreach via Python bridge script / Docker environment (`scripts/openoutreach_bridge.py`).

### 2. LINE Linking & Tracking Integration
- Embed UTM-tagged LINE Official Account QR code / links in OpenOutreach outbound emails.
- When prospects click & bind in LINE, `line_linking.py` automatically tags the patient as a "B2B Corporate VIP".

### 3. Strict Pricing & Security Rules (AGENTS.md Compliance)
- OpenOutreach email prompt generator MUST NOT output explicit treatment prices (e.g. $8000, 60000元).
- Redirect prospects to booking VIP consultation links or requesting official corporate partnership brochures.

### 4. Dashboard BI Funnel Analytics
- Add "🏢 企業地推轉化榜 (Corporate Outreach ROI)" to `src/templates/dashboard.html` (`tab-analytics`).
- Track outreach emails sent, open rates, LINE bindings, and patient appointment conversions in `clinic.db`.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

- `AGENTS.md` — Section 3 Strict Pricing Security Rules & Agent identity
- `src/api/routes/dashboard.py` — Web Dashboard endpoints & Analytics tab APIs
- `scripts/mitm_interceptor.py` — Reference pattern for standalone python CLI scripts in `scripts/`

</canonical_refs>

<specifics>
## Specific Ideas

- OpenOutreach URL: https://github.com/eracle/OpenOutreach
- Use Bayesian Active Learning on lead profile embeddings to refine local target company search.
- Connect with `clinic.db` to record corporate lead interaction logs.

</specifics>

<deferred>
## Deferred Ideas

- Direct automated B2C cold emailing to individuals (Focus strictly on B2B corporate partnerships).
- Third-party SaaS cold email subscriptions (Apollo/Instantly) — stick to local self-hosted OpenOutreach engine.

</deferred>

---

*Phase: 06-openoutreach-b2b-local-outreach*
*Context gathered: 2026-07-23*
