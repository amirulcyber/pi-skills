# Browser Supervisor — interface contract v0.1 (DRAFT, awaiting owner sign-off)

Distilled from the 2026-09-23 8x8 Connect session RCA (owner-reviewed).
Architecture: **Planner** (agent reasoning) / **Driver** (deterministic
execution) / **Supervisor** (budget + failure classification + handoff).
The driver NEVER improvises; the planner NEVER talks to the browser except
through these primitives; the supervisor NEVER executes.

Status: CONTRACT ONLY — no implementation until owner approves.

## Execution hierarchy (escalation order, fixed)

1. Official API / supported integration (preferred; UI is bootstrap-only)
2. Stable browser automation via these primitives, with explicit state inspection
3. Human handoff for auth, CAPTCHA, clipboard, credentials, show-once secrets
4. Browser/network diagnostics (debugging only, not task completion)
5. Specialized automation (anti-detect, gate passage) — last resort, logged

Non-negotiable rules:
- **Attempt budget:** max 3 attempts per micro-goal. A 4th attempt requires
  a NEW hypothesis, not persistence.
- **Failure-mode change ⇒ stop.** If failure 2 differs in kind from failure 1,
  escalate; do not add a third variant of the same idea.
- **Show-once values:** exactly one automated capture attempt, then handoff.
- Every primitive returns structured JSON. Screenshots are EVIDENCE, never
  the primary observation channel.

## Primitive contract

Every primitive returns:
```json
{"op":"click","ok":true,"data":{...},"evidence":"sel=…","ms":412}
{"op":"click","ok":false,"fail_class":"locator","error":"timeout",
 "observed":"3 elements matched, none visible","ms":15000}
```
`fail_class` ∈ `transient | locator | state | security-boundary | unsupported`
(see taxonomy). `observed` is a machine-readable description of actual page
state at failure time — the agent must not need a screenshot to classify.

### Navigation & state
- `navigate(url)` → final URL + title + `redirected:bool`. Fails with
  `security-boundary` on bot-wall markers (cf-challenge, recaptcha, 403 WAF).
- `inspect(scope?)` → structured page summary: URL, title, forms with field
  names/types/visibility, buttons with text/enabled, nav items with disabled
  state, iframes with src. THIS is the primitive that was missing — every
  task starts here instead of screenshot-reading.
- `wait_for(desc, timeout)` → `{ok, elapsed}`; desc = observable condition
  (url-pattern, selector-visible, text-present), never a blind sleep.
- `assert(cond)` → boolean + observed state. Used by supervisor to verify
  success conditions; a task is NOT complete until assert passes.

### Interaction
- `find(desc)` → ranked candidate list: `{selector, tag, text, visible,
  enabled, rect}`. Resolution happens BEFORE clicking; click targets are
  chosen from find() results, never guessed.
- `click(target)` → post-click URL + new dialogs/modals detected. Target =
  find() result or coordinates (coordinates = last resort, logged as such).
- `type(target, text, {clear:true})` → final field value + length returned.
  `clear:true` is default; appends require explicit opt-in (the 36→54-char
  bug). Returns actual value — caller verifies content, not intent.
- `select(target, option)` → chosen value. Custom dropdowns: open via real
  input, choose via keyboard, verify by reading back the committed value.
- `keypress(key)` / `clipboard_read()` → string (requires user-activation
  click first; returns `security-boundary` failure if permission denied).

### Observation
- `capture_network(filter, {since_op})` → requests/responses (status, url,
  body ≤ N KB) captured AFTER the hook is installed; hooks must be
  (re-)installed by the supervisor after any navigation — the driver flags
  `hooks_stale:true` when a navigation occurred since installation.
- `read_console()` → errors/warnings since last call.
- `screenshot(path)` → path. Budgeted: supervisor may refuse (screenshots
  are the expensive channel; use when structured obs is insufficient).

### Lifecycle
- `reset()` → reload/navigate-to-known-state; reports whether auth state
  survived (cookies valid) — the session-continuity check that was missing.
- `handoff(reason, instructions)` → terminal op. reason ∈ `auth | captcha |
  clipboard | show-once-secret | policy`. Must include exact human steps and
  what to paste back. Ends the automation attempt; supervisor logs it.

## Failure taxonomy (supervisor decision table)

| class | meaning | supervisor action |
|---|---|---|
| transient | timeout, network blip, one-off render race | retry same op (≤2) |
| locator | element not found/ambiguous/covered | re-run find(), alternate locator (counts as attempt 2) |
| state | app state wrong (wizard step, gated nav, expired session) | reset() then re-plan; if repeated → handoff |
| security-boundary | captcha, WAF, permission, credential wall | **immediate human handoff** — never automate around |
| unsupported | capability outside driver (worker-isolated data, privileged API) | stop + document; do NOT improvise |

Evidence-based retry: retry only with a hypothesis that differs from the
failed attempt. "Try again" is not a hypothesis.

## Task file format (what the planner writes before touching the browser)

```yaml
goal: obtain API key value for sms.8x8.com testing
preconditions: [authenticated session, api-keys page reachable]
actions:
  - navigate: https://connect.8x8.com/messaging/api-keys
  - click: {find: "row action copy-icon", verify: "clipboard non-empty"}
  - clipboard_read
success: clipboard matches /^[A-Za-z0-9]{30,}$/ and ends with table suffix
max_attempts: 3
fallback: handoff("clipboard", "click copy icon on row h1-testing9, paste key")
never: [create additional keys, brute-force masked value]
```

## 2026-09-23 8x8 session — measured cost of the old pattern

- ~20 micro-cycles (screenshot+reason each) for: login, form, key create,
  key retrieve. 4 keys created (3 deleted). Key finally obtained via
  coordclick + clipboard readText with user activation — the 1-op solution
  found only after exhausting wrong ones.
- Under this contract: inspect → find(copy-icon) → click → clipboard_read
  ≈ 4 driver ops, ≤1 screenshot.

## Implementation notes (post-approval)

- Substrate: CDP-attached Chromium (vnc-browser.sh pattern) for ops 1–2 of
  the hierarchy; Camoufox wrapper implements the SAME primitive subset for
  gate-passage contexts (fail `unsupported` where it can't comply).
- `security-boundary` failures are always surfaced to the planner as
  handoff candidates — the driver must not retry them internally.
- Secrets returned by primitives (keys, tokens) are written to
  `session/` (600, git-ignored) by the driver, never echoed to logs.
