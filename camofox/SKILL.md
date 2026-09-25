---
name: camofox
description: Camoufox anti-detect browser (Firefox fork, C++-level stealth) for Cloudflare/bot-walled targets. Use when vanilla Playwright sticks on "Just a moment"/Attention/captcha-gated pages AND the target is in AUTHORIZATION.md scope. Not a captcha solver — fingerprint consistency. Never for walls the program forbids.
---

# Camofox — anti-detect browsing

Engine: `camoufox` 0.5.6 (PyPI) = same core as `jo-inc/camofox-browser`
(which wraps it via `camoufox-js`). Installed in `~/.venvs/cfvenv`
(home disk — /tmp too small). Binaries via `camoufox fetch`
(`~/.cache/camoufox`). No API key, no secrets.

## Recipe (earned 2026-09-21 vs Moneybox Cloudflare)

```python
from camoufox.sync_api import Camoufox
with Camoufox(headless=False, geoip=True,   # geoip needs camoufox[geoip]
              proxy={"server": "socks5://127.0.0.1:18080"}) as browser:
    pg = browser.new_page()
    pg.goto(url, timeout=120000)
```

- **Headed + geoip is the combo that works.** Headless sticks on CF;
  headed without geoip leaks timezone/locale vs proxy IP (LeakWarning).
- **Needs Xvfb**: `DISPLAY=:99` — that display already runs on **saturn**; on
  neotokyo there is no X server, so start one (`Xvfb :99`) or run headless and
  expect it to stick on Cloudflare. Scratch paths here are saturn's; the
  neotokyo scratch dir is `/tmp/opencode` (see the host table in `../AGENTS.md`).
- **Memory**: one browser at a time (~400MB); kill strays with
  `pkill -f "[c]hrome-linux"` / `[f]irefox` bracket patterns (never a
  pattern present in your own command line — it suicides the shell).
- Human primitives live in `/tmp/human.py` (`htype`/`hclick`/`hmove_to`)
  — importable from Camoufox pages (same Playwright API).
- Screenshots to `/tmp`, never commit.

## Scope rules (same as capmonster)

- Authorized targets only (`AUTHORIZATION.md`). Passing a bot-wall to
  continue scoped testing = gate passage, logged with timestamp.
- NEVER file wall-passage as a finding. NEVER brute-force through it.
- Cloudflare "Just a moment" that auto-clears <60s headless-vanilla:
  prefer vanilla (cheaper). Camofox is for persistent walls.

## Usage log

- 2026-09-21 Moneybox CF managed-challenge: vanilla stuck 60s+ on both
  egresses; Camoufox headed+geoip+residential loaded homepage in 10s.
