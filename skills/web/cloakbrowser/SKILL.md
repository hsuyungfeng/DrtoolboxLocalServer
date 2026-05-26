---
name: cloakbrowser
description: Use CloakBrowser (stealth Chromium) for web browsing when standard browser tools get blocked by bot detection (Cloudflare, reCAPTCHA, FingerprintJS). Drop-in Playwright replacement with 58 source-level C++ patches.
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [browser, stealth, bot-detection, playwright, cloakbrowser]
    related_skills: [dogfood, webapp-testing]
---

# CloakBrowser — Stealth Browser for Bot-Detection-Bypassed Sites

CloakBrowser is a stealth Chromium binary with 58 source-level C++ patches that passes bot detection systems (reCAPTCHA v3, Cloudflare Turnstile, FingerprintJS, BrowserScan, ShieldSquare, Kasada, Akamai). It is a **drop-in Playwright replacement** — same API, just swap the import.

**Current version:** v0.3.30 (Chromium 146.0.7680.177.5)
**Installed at:** `/home/hsuyungfeng/DrtoolboxLocalServer/.venv/lib/python3.12/site-packages/cloakbrowser/`
**Binary cache:** `~/.cloakbrowser/` (~200MB Chromium binary)

## When to Use

- The built-in `browser` toolset gets blocked by bot detection (Cloudflare, reCAPTCHA, etc.)
- Need to scrape or interact with anti-bot protected sites
- Need to access sites that require human-level fingerprint (reCAPTCHA v3 score 0.9)
- Standard HTTP requests (`requests`, `curl`) fail due to TLS fingerprinting or JS challenges

## When NOT to Use

- Simple page inspection (use built-in `browser` tools first)
- Local web app testing (use `webapp-testing` skill)
- Sites without bot detection (standard tools are faster)
- When you need visual inspection (use `browser_vision` or `vision_analyze`)

## Quick Start

### Verify Installation

```bash
pip show cloakbrowser
python -m cloakbrowser info
```

### First Run — Binary Download

On first use, CloakBrowser auto-downloads the stealth Chromium binary (~200MB):

```python
from cloakbrowser import launch

browser = launch()
page = browser.new_page()
page.goto("https://example.com")
print(page.title())
browser.close()
```

### With Stealth Features

```python
from cloakbrowser import launch

browser = launch(
    headless=True,       # or False for headed mode
    humanize=True,       # human-like mouse, keyboard, scroll
    geoip=True,          # auto-detect timezone/locale from proxy IP
)
page = browser.new_page()
page.goto("https://protected-site.com")   # no more blocks!
browser.close()
```

### With Proxy

```python
browser = launch(
    proxy="http://user:pass@proxy:8080",  # HTTP proxy
    # proxy="socks5://user:pass@proxy:8080",  # SOCKS5 proxy
    geoip=True,
    humanize=True,
)
```

### Persistent Profile (cookies survive restarts)

```python
from cloakbrowser import launch_persistent_context

ctx = launch_persistent_context("./my-profile", headless=True)
page = ctx.new_page()
page.goto("https://example.com")
# cookies and localStorage persist across restarts
ctx.close()
```

## Common Patterns

### Web Search / Content Extraction

```python
from cloakbrowser import launch

browser = launch(headless=True, humanize=True)
page = browser.new_page()

# Navigate and wait for full render
page.goto("https://search.example.com?q=your+query")
page.wait_for_load_state("networkidle")

# Extract content
title = page.title()
text = page.text_content("body")
links = page.evaluate("""
    () => document.querySelectorAll('a[href]').map(a => a.href)
""")

print(f"Title: {title}")
print(f"Text length: {len(text)}")
browser.close()
```

### Screenshot for Visual Inspection

```python
page.screenshot(path="/tmp/cloak_screenshot.png", full_page=True)
# Then use vision_analyze("/tmp/cloak_screenshot.png", "What do you see?")
```

### Form Filling (reCAPTCHA-safe)

```python
# CRITICAL: Use page.type() NOT page.fill() for reCAPTCHA-safe form filling
page.type("#email", "user@example.com", delay=50)  # realistic keystroke delay
page.type("#password", "secret", delay=50)
page.click("button[type='submit']")
```

### Wait for Elements (reCAPTCHA-safe)

```python
# CRITICAL: NEVER use page.wait_for_timeout() — reCAPTCHA detects CDP timing
# Use native sleep instead:
import time
time.sleep(3)  # invisible to the browser

# Or wait for element visibility:
page.wait_for_selector("#result", state="visible")
```

## API Reference

| Function | Purpose |
|---|---|
| `launch()` | Basic stealth browser launch |
| `launch_async()` | Async version |
| `launch_context()` | Browser + context in one call (UA, viewport, locale, timezone) |
| `launch_context_async()` | Async version |
| `launch_persistent_context()` | Persistent profile (cookies survive restarts) |
| `binary_info()` | Check installation status |
| `clear_cache()` | Force re-download |
| `ensure_binary()` | Pre-download binary (e.g. Docker build) |

### Key `launch()` Options

- `headless=True/False` — headed mode (some sites detect headless)
- `proxy="http://..."` or `proxy="socks5://..."` — HTTP or SOCKS5 proxy
- `geoip=True` — auto-detect timezone/locale from proxy IP
- `humanize=True` — human-like mouse, keyboard, scroll (Bézier curves, per-char typing)
- `human_preset="careful"` — slower, more deliberate movements
- `timezone="America/New_York"`, `locale="en-US"` — manual override
- `args=["--fingerprint=42069"]` — fixed fingerprint seed (consistent identity)
- `args=["--fingerprint-platform=windows"]` — cross-platform spoofing
- `stealth_args=False` — disable default stealth flags

## Important Pitfalls

1. **Never use `page.wait_for_timeout()`** — reCAPTCHA detects CDP timing signals. Use `time.sleep()` instead.
2. **Use `page.type()` not `page.fill()`** — `fill()` sets values directly without keyboard events, which reCAPTCHA flags.
3. **Minimize `page.evaluate()` calls** before reCAPTCHA fires — each sends CDP traffic.
4. **Wait for `networkidle`** before inspecting DOM on dynamic pages.
5. **Space out requests** — back-to-back requests from same session get penalized. Wait 30+ seconds between pages with reCAPTCHA.
6. **Use residential proxies** for IP reputation — datacenter IPs are flagged.
7. **Spend 15+ seconds on the page** before triggering reCAPTCHA — short visits score lower.
8. **Linux font requirements** (for Kasada/Akamai): `sudo apt install -y fonts-noto-color-emoji fonts-freefont-ttf fonts-unifont fonts-ipafont-gothic fonts-wqy-zenhei fonts-tlwg-loma-otf`

## CLI Commands

```bash
python -m cloakbrowser install      # Download binary
python -m cloakbrowser info         # Show version, path, platform
python -m cloakbrowser update       # Check for newer binary
python -m cloakbrowser clear-cache  # Remove cached binaries
```

## Docker CDP Server Mode

```bash
docker run -d --name cloak -p 127.0.0.1:9222:9222 cloakhq/cloakbrowser cloakserve
```
Then connect via: `pw.chromium.connect_over_cdp("http://localhost:9222")`

## Resource Usage

- Idle: ~190MB RAM
- With 3 tabs: ~280MB RAM
- Each additional tab: ~30MB RAM
