---
name: web-optimise
description: PageSpeed/Lighthouse analysis and remediation for static sites (Jekyll on GitHub Pages). Use when asked to check site speed, after a PageSpeed report lands, or before/after front-end changes. Runs the same Lighthouse engine PageSpeed uses against the live site (local Chromium, no API quota), parses failures into an action list, and applies the proven remediation set — responsive WebP figures, tiny card thumbnails, lazy+dimensions, deferred third-party, stable cache keys, AA contrast.
---

# web-optimise

Grounded in two optimisation rounds on `amirulcyber.github.io` (Jekyll + GitHub
Pages, Sep 2026) that took mobile lab to 0.95–1.0 and desktop to 1.0, with
Accessibility/Best-practices/SEO at 1.0. Every step below traces to a finding
that actually appeared in a report — not generic advice.

## The failure taxonomy (what reports actually flag on small static sites)

| Finding | Root cause on our site | Fix (script/step) |
|---|---|---|
| `image-delivery-insight` ~350 KiB | Essay cards rendered 160×90 but served 190 KiB full-size JPGs | `mk-webp.sh --thumb` + `<picture>` in card include |
| Post figures ~2 MB | 10× 1616px JPGs, no lazy, no dimensions, no modern format | `mk-webp.sh` 800/1200w + `figure.html` include pattern |
| `unused-javascript` ~140 KiB | GTM `gtm.js` + `gtag/js` compete with LCP | Delayed GTM loader (idle/interaction/timeout), keep `dataLayer` queuing |
| `cache-insight` | GitHub Pages forces `max-age=600`; plus our `?v=site.time` busted cache every build | Short-SHA-or-date version key (never pipe a SHA through `date`) |
| `color-contrast` (a11y 0.95) | Accent `#a3661f` on paper = 4.38:1, just under AA | `contrast.py` then darken to `#8a5a1a` (5.51:1) |
| `render-blocking-insight` | 20 KiB `style.css` blocks FCP | Accept at this size; inline only if FCP actually suffers |

Known ceilings (report as accepted, do not chase):

- Pages `max-age=600` means `cache-insight` never fully clears — shrink the
  bytes instead (thumbnails took it 406 → 102 KiB).
- GTM/Umami will always trip `unused-javascript`. Delaying GTM cut TBT to
  60–100 ms; removing it entirely costs bounce pageviews. Owner's call.
- PSI API anonymous quota (`429`) is routinely exhausted — that is why this
  skill audits locally instead of calling the API.

## Workflow

1. **Baseline** — `scripts/lh-audit.sh <url> [extra-url...]` runs mobile +
   desktop Lighthouse with local Chromium and saves JSON to an out dir.
   Re-run twice on mobile; TTFB noise from the sandbox→edge path swings lab
   scores ±0.04, so compare medians, not single runs.
2. **Parse** — `scripts/lh-parse.py <json>` prints categories, metrics, and
   every failing opportunity/insight with byte savings and offending nodes.
   Fix in impact order (bytes first): images → third-party → cache keys →
   contrast → render-blocking.
3. **Remediate** — apply the patterns below, scoped to the flagged files.
4. **Verify** — wait for Pages deploy (poll for the new `?v=` hash), re-run
   `lh-audit.sh`, diff with `lh-parse.py`. Expect: `image-delivery` and
   `color-contrast` cleared, `cache-insight` down ~75%, categories ≥ 0.95.
5. **Ship** — commit flow per `git-amirulcyber`: status → diff-check →
   stage named files → commit → push to `main` (or a branch if asked).

## Remediation patterns (Jekyll)

**Responsive figures** — pre-generate siblings (`mk-webp.sh`):
`photo-800.webp` / `photo-1200.webp` beside `photo.jpg`; wrap in
`<picture>` with `srcset … 800w, … 1200w`, `sizes` matching the content
column, `loading="lazy" decoding="async"` + explicit `width/height` on the
`<img>` (kills CLS). First/hero image: `eager` + `fetchpriority="high"`,
no lazy. Strip per-image `?v=` busters — they defeat the cache.

**Card thumbnails** — never serve the full figure into a 160×90 box.
Pre-generate 320×180 cover-crops (`-320.webp` + `-320.jpg` fallback, ~7 KiB)
and point the card include at those via `<picture>/<source sizes="…">`.

**Delayed GTM** — initialise `window.dataLayer` + push `gtm.start`
immediately (cheap, preserves queuing); inject the external `gtm.js` on
`requestIdleCallback` (3 s timeout) / first scroll-touch-click-keydown /
`load`, with a 6 s safety net. Add `preconnect` for the tag hosts and keep
small first-party scripts `defer`.

**CSS version key** — `site.time`-per-second busts cache every build.
Use the Pages build revision when present, else a daily date. Liquid gotcha:
**never** `{{ sha | date: … }}` — the `date` filter mangles a hex SHA into
a bogus 1983 date. Use an explicit branch:

```liquid
{%- if site.github.build_revision -%}
  {%- assign css_v = site.github.build_revision | slice: 0, 7 -%}
{%- else -%}
  {%- assign css_v = site.time | date: '%Y%m%d' -%}
{%- endif -%}
<link rel="stylesheet" href="{{ '/assets/css/style.css' | relative_url }}?v={{ css_v }}">
```

**Contrast** — check every text/background pair with `contrast.py`
(needs ≥ 4.5:1 for body text). Darken the lighter side; verify both themes
if the site has a dark mode.

## Scripts

- `scripts/lh-audit.sh` — needs `node`/`npx`, `lighthouse` (auto-installed
  into a scratch dir), and a Chromium (`CHROME_PATH`, Playwright cache, or
  system chrome). `--check` verifies the toolchain without auditing.
- `scripts/lh-parse.py` — stdlib only. Prints scores, metrics, failing
  audits with savings, and node selectors for image/contrast failures.
- `scripts/mk-webp.sh` — needs ImageMagick `magick`. Generates responsive
  WebP (+JPG fallback) rungs or 320×180 card crops. Never upscales
  (`…x>` shrink-only for the large rungs).
- `scripts/contrast.py` — stdlib only. WCAG 2.x contrast ratio for hex
  pairs, PASS/FAIL against 4.5 (AA normal) / 3.0 (AA large).
