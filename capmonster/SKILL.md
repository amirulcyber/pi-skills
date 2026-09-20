---
name: capmonster
description: Paid CapMonsterCloud captcha solving for AUTHORIZED engagements — pass automation gates (reCAPTCHA v2/v3/Enterprise) to continue recon and vulnerability testing. Use when a scoped target walls automation with a captcha AND the owner authorized solver use. NEVER for brute-force, credential attacks, or as a bypass finding. Every spend is logged with timestamp.
---

# CapMonster — gate passage, not gate breaking

Paid key on file (owner-provided 2026-09-20, ~$4.99). Client:
`capmonster.py` (stdlib only). Key in `.env` (600, gitignored — verified
by `git check-ignore`; never print, never commit, never send anywhere
except `api.capmonster.cloud`).

## Authorization scope (owner-set 2026-09-20, standing until revoked)

- ✅ Solve captchas to CONTINUE testing inside `AUTHORIZATION.md` scope
  (login flows, form submits, signup gates on owned test accounts).
- ❌ NEVER brute-force credentials through a solved gate (one legit
  credential attempt per gate at most — session login, own account).
- ❌ NEVER file gate-passage as a vulnerability ("captcha bypass").
  If a gate falls to mere replay/solvers trivially AND the program pays
  for it, that is a human decision with the owner first — default NO.
- ✅ Log EVERY solve in the engagement triage log: timestamp (UTC),
  gate, task type, cost, and the mandatory note: gate cannot be passed
  without the solver (automation-gated, not bypassed).

## Usage

```python
import sys; sys.path.insert(0, "~/piworkspace/pi-skills/capmonster")
from capmonster import get_balance, solve
get_balance()  # pre-flight: know the budget
token = solve({"type": "RecaptchaV2TaskProxyless",
               "websiteURL": "https://www.grammarly.com/signin",
               "websiteKey": "<sitekey from page>"})
# v3: {"type":"RecaptchaV3TaskProxyless", ..., "minScore":0.3,
#      "pageAction":"<action>"}
```

Then inject `token` into the page's `g-recaptcha-response` field (v2) or
submit handler (v3) via page flow — the surrounding test continues
unchanged. `solve()` polls up to 180s, aborts past $0.50/solve.

CLI: `python3 capmonster/capmonster.py` prints balance (spend: $0).

## Cost discipline

- Balance check before each session; stop at <$1 without owner refill nod.
- v2 checkbox ≈ $0.0008–0.002, v3 ≈ $0.0002–0.0006, Enterprise higher.
- One solve per gate attempt; repeated failures = STOP (gate adapted),
  never burn the balance retrying a losing shape.

## Usage log (append every spend)

- 2026-09-20 skill created; balance $4.9916 at 18:33 UTC. No solves yet.
- 2026-09-20 18:41Z ZECIBLE contact v3 (sitekey `6Lfa…`, action
  `contactform`): token injected → send refused. $0.0009.
- 2026-09-20 18:42Z same gate, `grecaptcha.execute` override → refused.
  $0.0009. Verdict: not score-related; STOP on this shape. Balance $4.9898.
- 2026-09-20 18:55Z Grammarly invisible-Enterprise: enterprise task →
  instant INVALID_SITEKEY; plain-v2 task → worker failed same way ~3min.
  $0 spent. STOP — key enterprise-bound. Balance $4.9898.
