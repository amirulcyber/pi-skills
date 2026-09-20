---
name: jev
description: TypeSafe JEV (System One) structured decisions for the bug-bounty loop — triage classification, severity calibration, duplicate/novelty checks on SANITIZED states. Use when a probe returns and you need a fast calibrated second opinion, when ranking candidate findings, or when checking matrix coverage. NEVER for secrets, creds, tokens, PII, or customer data.
---

# JEV — calibrated decisions for bounty work

JEV (`openjev-latest` via `api.codiv.ai/v1/systemone`) is not chat: state in,
typed probabilities out. 70–500ms, ~152 input tokens for a triage call, zero
output tokens metered. It cannot hallucinate text — it only distributes
probability over YOUR labels. Verified 2026-09-20 (see usage log below).

## Rule 0 — non-privileged data ONLY (no exceptions)

JEV is a third-party API. Sendable: response shapes/codes, verdict
rationales, methodology notes, public recon, redacted structures.
NEVER sendable: passwords, session cookies, `csrf-token` values, API keys,
mailbox contents containing live tokens/links, customer PII, anything under
`/tmp/*.env`, `*-state.json`, `*-link.txt`. Sanitize first, then call.
A state containing a secret is a finding about YOU, not the target.

## API shape (reverse-engineered 2026-09-20, no public docs)

- `POST {BASE}/v1/systemone`, Bearer key, JSON body:
  `{"model":"openjev-latest","state":"…","questions":{…}}`.
- Question types (exact; others 422):
  - `{"type":"noul"}` → `{"noul": p}` baseline probability.
  - `{"type":"choice","criteria":{label: description,…}}` →
    `{"choice": winner, "probabilities": {label: p}, "confidence": c}`.
  - `{"type":"score","criteria":[lvl0…lvlN]}` (2–10 ordered levels) →
    `{"score": float-index, "legend": {i: lvl}, "probabilities": {i: p},
    "confidence": c}`.
- `GET {BASE}/v1/models` lists aliases (`openjev-latest` → `openjev-0.1`).
- Quota observed: 100M tokens (JEV), 10M (diffusiongemma-26b text).

## Client (`jev.py`, stdlib only — no `typesafe-sdk` needed)

Key lives in `.env` beside the script (600, gitignored — verify with
`git check-ignore jev/.env` before any commit touching this dir).
Env vars override `.env`.

```python
import sys; sys.path.insert(0, "~/piworkspace/pi-skills/jev")
from jev import decide, score, null_prob
decide(state, vulnerable="…", secure="…")   # choice verdict
score(state, ["very unlikely","unlikely","likely","very likely"])
null_prob(state)                            # baseline
```

CLI smoke: `python3 jev/jev.py "some state"` (no secrets on argv on shared
hosts — prefer env/file for real states).

## Bounty-loop recipes (where JEV supplements, not replaces)

1. **Triage second opinion** (proven 2026-09-20): feed the SANITIZED probe
   outcome (status + shape, e.g. `{"status":"ERROR","error":"link already
   used"}` + one-line context) with `vulnerable/secure` criteria. Cost:
   ~150 tokens, <1s. It agreed with all our banked verdicts in testing.
   It does NOT replace the triage log — log first, ask second.
2. **Severity calibration**: `score()` a redacted finding summary on
   `["info","low","medium","high","critical"]` before writing the report.
   A second number against your own rating; investigate disagreements.
3. **Duplicate/novelty pre-check**: state = redacted technique + target
   class; choice over `{known-pattern:…, novel-shape:…}`. Weak signal —
   program taxonomies still rule; never file off JEV alone.
4. **Coverage check**: state = matrix cells + verdicts (no secrets);
   choice over `{complete:…, gap:…}` per cell to catch untested cells.
5. **What JEV never does**: exploit, bypass, enumerate, hold session,
   touch credentials, or see raw evidence. Evidence stays in `/tmp` + logs.

## Usage log (append; costs honesty)

- 2026-09-20 schema probe: `noul`/`choice`/`score` shapes mapped via 422s
  (~6 tiny calls, <1K tokens). Choice on real banked outcome (reset-reuse
  rejection) → `secure` 0.999, confidence 0.99 — agrees with filed verdict.
- 2026-09-20 state-precision lesson: sloppy states flip verdicts ("HTTP 200
  status ERROR" → `vulnerable` 0.59, conf 0.03; rewritten precisely →
  `secure` 0.999, conf 0.99). JEV judges YOUR WORDS: write states as
  explicit outcome sentences (who did what, what refused/succeeded).
  Distrust any answer with confidence <0.5 — rewrite the state, don't file.
- 2026-09-20 batch: 5 sanitized banked verdicts re-judged (~115 tokens
  each): referer/totp/invite agreed first pass; reuse/host-header agreed
  after precision rewrite. Total spend ≈ 1.5K tokens.
