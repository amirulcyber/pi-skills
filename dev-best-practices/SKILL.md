---
name: dev-best-practices
description: App-dev quality discipline for the Python/Bash pipelines and TypeScript/Node (pnpm) tooling I build and maintain (intel-monitor, zoneh, pentest scripts, ts-ps-app). Use when writing new code, before/after edits, when a silent failure or contract bug bites, or when auditing/reviewing code. Leads with fail-loud design, typed contracts, and regression tests — the layers that actually caught real bugs — with NASA/JPL Power-of-Ten rules and static analysis as the supporting floor.
---

# Dev Best Practices

Grounded in the failure classes that actually bit Zone-H and intel-monitor — not
generic "clean code" advice. Every rule below traces to a real incident.

## The failure taxonomy (why these rules exist)

| Failure | Caught by |
|---|---|
| Filename contract drift (scrape vs run_daily) | integration/contract test |
| Field-map mismatch (`notifier`→`attacker`) | typed boundary + selftest |
| mirror_id regex searched the wrong scope | targeted regression test |
| schema_version producer/consumer drift | versioned contract + fail-closed |
| 0-entry silent no-op | fail-closed + heartbeat table |
| argparse IndexError on missing value | regression test |
| Groq model removed upstream | fail-loud API wrap + monitor |
| LLM classifier decommissioned (allam-2-7b) | golden-sample regression test (live canary) |
| host git reset clobbered uncommitted code | commit-first + porcelain guard |
| malformed-body parse missed `IndexError` (empty `choices`) | single-exception boundary parser |
| parser regex matched the wrong same-pattern element (POS doc matched gallery images) | live-response golden fixture |
| two-writer column clobber (list rerun wiped detail enrichment) | disjoint upsert paths + non-clobber regression test |
| dead imports / unused noqa | ruff (rule 11) |

Takeaway: static tools only caught the **last** one. The rest were caught by fail-loud
design + contract/regression tests. Lead with those; treat linters as a floor, not the fix.

## Layer 1 — Fail-loud core (non-negotiable)

- Every pipeline run emits machine-readable state: a status line (`# STATUS {...}`) and/or
  a heartbeat table row (`runs`), written on **every** outcome (success, failure, 0-entry).
- Failures exit non-zero. Never silently succeed with empty/partial output.
- **Fail-closed over fail-open**: a broken contract (missing/wrong `schema_version`,
  malformed file, non-list `entries`) is a hard failure — never a silent 0-entry no-op.
- Pre-flight self-test (`selftest()`) must be **dependency-free** so cron can run it
  (no pytest in the cron path).
- Health checks read machine state (status line / table), never grep log prose.
- **Bulk runs: save partial results, still exit non-zero.** A per-item failure (one bad
  Detail page out of 37) is collected with its id, successes are persisted, and the run
  exits 1 with the failed ids reported — never a silent all-or-nothing, never a quiet
  zero-failure success. (Caught 2026-09-04: elelong `--details`.)

## Layer 2 — Typed contracts at boundaries

- Every producer→consumer boundary carries an explicit versioned schema
  (`schema_version` in the payload, asserted on ingest).
- Model inter-component data as `TypedDict`/dataclass, **not** raw `dict`. This is what
  makes static typing (pyright) actually bite on field-name drift instead of being theater.
- Field mapping is centralized and round-trip tested (selftest).
- One source of truth for shared constants — import them, never duplicate.
- **Two writers, one table: partition columns by producer.** When list-scrape and
  detail-scrape both upsert the same table, each path writes only its own columns
  (list path never touches detail columns and vice versa), plus a regression test
  proving a list-only rerun does not wipe detail enrichment. (Caught 2026-09-04:
  elelong `upsert_results` vs `upsert_detail_properties`.)

## Layer 3 — Regression test per bug

- For every fixed bug, write the test that would have caught it (the two-row mirror_id
  test is the template).
- Test **failure paths**, not just happy paths: 0-entry, schema mismatch, exception
  boundary, malformed input, missing arg.
- pytest must run without live services (mark live/CAPTCHA tests as skips).
- **Test mocks must be isolated per test**: build them with `__init__` instance attrs or
  factory functions — never mutable class attributes. A test that mutates a shared mock
  silently pollutes every later test in the run (caught 2026-08-31: `test_defacement_search.py`
  `MockDefacementSearchConfig` class attrs leaked `enabled=False` across tests).
- **Golden-sample tests for LLM filters**: when a pipeline step depends on an LLM's
  judgment, hard-code ~2 known true-positives + ~10 known true-negatives and assert the
  live model classifies them correctly. This is the decommission canary — an upstream
    model retirement otherwise surfaces only as a silent zero-save. Mark it `integration`
    (excluded from the default gate) and wire it into the daily health check.
- **Golden-sample tests for parsers**: one **captured live response** as a fixture,
  not just hand-built HTML. Synthetic fixtures re-encode your assumptions and pass
  trivially; only a real page catches pattern collisions (e.g. a doc-ID regex matching
  gallery images before the target iframe). Refresh the capture when the upstream
  markup legitimately changes. (Caught 2026-09-04: elelong Detail fixture.)
- **Delete untestable defensive branches; don't pragma them.** If a guard cannot be
  triggered by any input (e.g. an `isinstance(x, list)` check after a `[...]`-anchored
  regex, where `json.loads` either yields a list or raises), it is dead code under
  rule 11 — remove it instead of `# pragma: no cover`.

## Layer 4 — External dependency drift

- Wrap every upstream API call (Groq, 2Captcha, RSS) so errors **fail loud** and are
  surfaced by the health check — never logged-and-forgotten.
- Distinguish transient (retry with backoff + jitter, bounded attempts) from permanent
  (fail fast). No unbounded retry loops.
- An upstream deprecation/404 is a contract break: surface it, don't swallow it.
- **Prefer the provider's plain REST endpoint over its SDK** (httpx/requests) when the
  SDK isn't already a pinned project dependency. One HTTP client for the whole collector
  = fewer deps to drift and one transport to test. (Bit 2026-08-31: system `python3` had
  httpx but not the `groq` SDK; the OpenAI-compatible REST call worked in both envs.)

## Layer 5 — Config & secrets (12-factor)

- Secrets via env vars only, never plaintext in code/config; validate config at startup
  (fail early).
- No secret may reach a commit, a log, or shell history.

## Layer 6 — Static hygiene floor (weakest layer — run it, don't worship it)

Mechanical rule→tool mapping:

| Rule | Tool |
|---|---|
| Dead code / unused imports (rule 11) | ruff F401, F841 |
| Unused noqa directives (rule 11) | ruff RUF100 |
| Check return values (rule 7) | ruff B018 + bash `pipefail` |
| Never swallow errors (rule 6) | ruff BLE001 |
| Typed boundaries (rule 6) | pyright (project-local `.venv`) |
| Forbidden APIs / recursion / unbounded loop / >60-line fn / assert density (rules 1/2/4/5) | nasa-lsp NASA01/02/04/05 |

**Shipped here as reusable assets:**
- `ruff.toml` — curated select `E4/E7/E9/F/B/BLE/I/RUF100`; **B018** (rule 7), **BLE001** (rule 6), and **RUF100** (rule 11) stay active; no global ignore list to rot.
- `lint.sh` — compile → selftest → pytest → ruff → pyright → nasa (advisory) → bash guard. Any project drops in a one-line `extend = "<SKILL_ROOT>/dev-best-practices/ruff.toml"` or calls `lint.sh` with env knobs `PY`, `SELFTEST`, `TEST_PY`, `PYRIGHT`.
- `bash-guard-check.sh` — flags unguarded `VAR=$(… grep …)` under `set -e` (the silent-abort class above); wired into `lint.sh` as the bash floor.
- `ts-qc-check.sh` — TypeScript/Node gate (see "TypeScript / Node tooling" below): pnpm build-approval sanity, placeholder-literal scan, lockfile-committed check, then `pnpm lint && pnpm typecheck && pnpm test`.

`<SKILL_ROOT>` = this skill's directory. Its absolute value is
`~/piworkspace/pi-skills` on both hosts today, but resolve it from the
marker-file table in `../AGENTS.md` rather than hardcoding it — the hosts are
meant to diverge again.

**Ruff workflow (2026-09-02 — do NOT copy the ruleset):**
- One canonical `ruff.toml` here; projects reference it via a 1-line `ruff.toml` containing
  `extend = "<SKILL_ROOT>/dev-best-practices/ruff.toml"`. Project-local `[lint]` overrides go in that
  project file, never in the shared one.
- Ruff is **pinned at 0.16.5**. Keep the durable binary in a host mount so it
  survives a container recreate, and symlink it onto PATH (neotokyo: durable bins
  are `~/piworkspace/.local/bin`; saturn: `~/.local/bin`). `lint.sh` pins the same
  version via `uvx ruff@0.16.5` so it stays reproducible even without the local install.
- Run **bare `ruff check .`** from any project that has the pointer — it resolves the curated
  set. Never run bare ruff with *no* config: that silently uses ruff defaults (S324, DTZ006, …),
  a different rule set that produces false-positive noise.

- `ruff check .` must be **clean** (zero warnings), not advisory.
- **ruff will NOT flag dead classes or functions** — F401 covers unused imports, F841
  unused locals, but a defined-and-never-called class/function passes silently. Only
  rule 11 (read every line) catches it. (Caught 2026-08-31: `SerperError` was defined
  but never raised.)
- nasa-lsp is **advisory**: its assert-density rule (NASA05) is miscalibrated for
  non-safety-critical scripts. Treat it as a checklist, not a gate.
- **Probe the tool before restructuring code.** When a linter flags obviously-correct
  code, reproduce with a minimal probe (5 lines) to distinguish a tool limitation
  from a real violation — then scope the suppression to the blind spot, never the
  codebase. (Caught 2026-09-05: Biome 2.5 does not analyze Svelte template
  expressions, so every markup-used variable read as "unused"; fixed with a
  `**/*.svelte`-only override, verified by probe, with svelte-check kept as the
  semantic gate.)

## Pre-write checklist (left-shift — run BEFORE writing)

1. Will any call recurse back to itself? (keep the call graph acyclic)
2. Does every loop have a provable bound? (an intentional `while True` daemon must be
   documented as provably non-terminating)
3. Is every opened resource closed on every exit path, including errors?
4. Will this function stay under ~60 lines / do one job?
5. What preconditions am I asserting — and do they fail loudly?
6. Am I swallowing any error silently? (every failure logged / raised / returned)
7. Is there a hidden side effect (I/O) inside an innocuously-named helper?
8. Is there a producer→consumer boundary here? If so, define its versioned schema now.
9. Am I leaving dead code / unused imports / "just in case" commented blocks?
10. What test will cover at least one failure mode of this code?

## The 12-rule audit (post-write — AI-aware layer)

Adapted from NASA/JPL *Power of Ten* (Holzmann), extended for AI-assisted dev. For each
violation cite `file:line` + snippet, tagged 🔴 critical / 🟠 high / 🟡 medium / 🟢 low:

1. **Keep it linear** — no >2-level nesting, no unbounded recursion.
2. **Bound every loop** — explicit, enforceable max iterations.
3. **Know what you own** — every resource closed on every path, incl. errors.
4. **One function, one job** — >60 lines or "and"-describable = decompose.
5. **State your assumptions** — assert contracts, esp. at trust boundaries.
6. **Never swallow errors** — no `except: pass`, no ignored return codes.
7. **Narrow your state** — no module globals used as passthrough.
8. **Surface your side effects** — I/O visible at the call site.
9. **One layer of magic** — no stacked decorators/dispatch obscuring flow.
10. **Warnings are errors** — linter/typechecker must block, not advise.
11. **Read every line** — dead code, unused imports, "just in case" blocks, generic names
    (`data`, `result`, `temp`) in critical paths.
12. **Tests first** — changed code needs a test covering ≥1 failure mode.

Verdict discipline: **PASS or FAIL only** — no "partial". Any violation = FAIL.

## Bash / cron silent-failure patterns (rule 7, adapted)

- Prefer `set -euo pipefail`; but `set -e` has gotchas — explicit checks are better.
- `cd "$dir" || { echo "…"; exit 1; }` — never bare `cd`.
- Never `cmd >/dev/null 2>&1` without checking the exit code.
- Intermediate pipe failures must not be masked (`pipefail`).
- **`VAR=$( … grep … )` under `set -e` is a silent abort.** `grep` returns 1 on
  no-match → `pipefail` makes the pipeline exit 1 → the bare assignment inherits
  it → `set -e` kills the script with *no output and no log line* (the daily
  report silently never fires). Guard every such capture with `|| true` / `|| echo ""`:
  `last_status=$(grep … | tail -1 || true)`.
  - `local x=$(grep …)` and `echo "$(grep …)"` *mask* the failure (exit 0) — no
    abort, but the value is silently dropped. Prefer the explicit `|| true`.
  - Caught 2026-08-27 in `check_intel_monitor.sh`: the new `# STATUS` grep had no
    guard and aborted the daily report before its output section. Fixing the class
    (not the instance) surfaced 8 more latent aborts in the same file.
  - Guard: `bash-guard-check.sh` (this skill) flags unguarded `VAR=$(… grep …)`
    under `set -e`; wired into `lint.sh`.
- **`out=$(cmd); rc=$?` never reaches `rc=$?` under `set -e`.** The assignment inherits
  the command's non-zero exit, so `set -e` aborts on the assignment line before the
  next statement runs. To capture an exit code deliberately, use the `if` form:
  `if out=$(cmd 2>&1); then rc=0; else rc=$?; fi`. (Caught 2026-08-31 in
  `check_defacement_search_model`: `out=$(pytest …); rc=$?` would have killed the entire daily
  check on the first failing golden test.)
- **Killing by cmdline pattern also matches your own shell.** A `for p in /proc/*;
  kill $p` loop whose pattern appears in its own command line (`*vite*dev*` inside
  `bash -c "... *vite*dev* ..."`) suicides mid-loop and hangs the session.
  Exclude self (`[ "$p" = "$$" ] && continue`, or `grep -v`) — or match the
  binary path instead of wrapper text. (Caught 2026-09-05 stopping a vite dev
  server.)
- **Verify kills took effect; check ports, not just PIDs.** Spawned servers can
  outlive a killed runner (orphaned, adopted, even zombie) while still holding
  their port — a later run then binds elsewhere or fails silently. After a
  sweep, re-scan AND probe the port (`curl --max-time … || echo down`); SIGTERM
  refusers need SIGKILL, and container zombies (state Z) are harmless once the
  port is free. (Caught 2026-09-05: four `node build/index.js` survivors.)
- **Prefer single-quote concatenation over backslash escapes inside `$( )`.**
  For embedded JSON use `-d '{"k": "'"$VAR"'"}'` — a stray `\"` leaves the
  string unterminated, swallowing the closing paren, and bash reports the
  failure far away (`syntax error near 'fi'`, real bug 17 lines up). When the
  reported line looks innocent, bisect backwards for unbalanced quotes.
  (Caught 2026-09-05 in `phase5-gate.sh`.)

## Source-of-truth discipline (git vs bind mount) — added 2026-08-31

- **Skills live in a bind-mounted host volume that a host-side `git reset`/`checkout`
  can silently clobber.** 2026-08-24 the D1 hybrid (`synthesize_wexb.py`) was edited
  in-place but never committed; a host working-tree reset at 14:07:30 rewrote 23 files
  across 6 skills, reverting the implementation. It was only recovered from a `.pyc`.
- **Commit before you consider it done.** Any skill change not in the host repo is one
  `git checkout .` away from vanishing. The host repo is the source of truth; the bind
  mount is a working tree, not a backup.
- **Guard destructive git ops on a dirty tree**: `git status --porcelain` must be empty
  before `reset --hard` / `checkout .` / `restore .` / `stash` — abort otherwise.
  (DECISIONS.md D14, ⏳ host `justfile` action.)
- **Forensics: never let `py_compile`/`import` overwrite evidence.** A surviving `.pyc`
  is a bytecode record; `python3 -m py_compile` silently overwrites `__pycache__` with a
  recompile. Copy evidence aside (or dump disassembly first) before recompiling.
  (The 2026-08-24 evidence `.pyc` was clobbered this way; a prior `dis` dump saved it.)

## TypeScript / Node tooling (added 2026-09-05)

Same fail-loud discipline applied to the TS/pnpm stack (ts-ps-app is the exemplar).

### Failure classes that actually bit

| Failure | Caught by |
|---|---|
| pnpm 11 auto-injected `allowBuilds: esbuild: "set this to true or false"` into `pnpm-workspace.yaml` during `pnpm rebuild` — placeholder shipped in a commit | `ts-qc-check.sh` |
| Two build-approval keys (`allowBuilds` + `onlyBuiltDependencies`) = two sources of truth | `ts-qc-check.sh` |
| Spec scenario claimed `tsc --noEmit` rejects explicit `any` — it doesn't; that's a lint rule | spec review rule below |
| `z.url()` accepted `http://`/`mysql://` while the error message claimed "postgres connection string" (wrong scheme passed validation, blew up at first connect) | negative wrong-scheme test + `ts-qc-check.sh` hint |
| `PG_MAX_CONNECTIONS` validated + exported + tested but never wired into the pg pool (silent no-op knob) | wiring regression test (config → consumer) |
| Biome emitted a warning but `biome check .` exits 0 — the `pnpm lint` gate passed | `biome check --error-on-warnings` |
| node-postgres `Pool` with no `'error'` handler crashed the process on an idle-client error (Postgres restart) | `pool.on('error')` handler |
| Biome 2.2+ folder-ignore drift (`files.ignore` gone; `!dir/**` → `!dir`) | `$schema` + warnings-as-errors gate |

### Rules

- **One build-approval setting.** pnpm 11 reads `allowBuilds` in `pnpm-workspace.yaml` (NOT the `pnpm` field in `package.json` — removed in v11; NOT `onlyBuiltDependencies` — superseded). Declare it explicitly; never let a bare `pnpm install`/`rebuild` be the moment config gets written.
- **pnpm mutates config files.** `pnpm install` / `pnpm rebuild` can edit `pnpm-workspace.yaml` (injecting `allowBuilds` placeholders). Re-read config after any install step and before commit; `ts-qc-check.sh` flags the injected placeholder.
- **Static floor (rule 10).** Biome 2.x config is `linter.rules.preset: "recommended"` + group keys (`suspicious.noExplicitAny: "error"`) — NOT 1.x `recommended: true`. Pin a `$schema` and let `biome check` fail the build.
- **`any` is a lint rule, not a tsc rule.** Strict `tsc --noEmit` does NOT reject explicit `any` — that is exactly why `noExplicitAny` exists. Write spec scenarios accordingly (lint catches `any`; tsc catches genuine type errors).
- **Lockfile is part of the build.** Commit `pnpm-lock.yaml`; CI uses `pnpm install --frozen-lockfile`. Never gitignore it.
- **Workspace `exports` → source is a dev convenience, not a prod build.** Before any "compiled output" claim, define the emit path (tsc build / tsup) and point `exports` at `dist/` + `types`. `noEmit: true` in a shared base is dev-only.
- **`engines` pins must match the toolchain pin** (mise.toml node vs package.json `engines.node`) — a loose `>=` next to an exact mise pin is drift.
- **A validator must enforce what its error message claims.** `z.url()` means "any valid URL", not "postgres connection string". Negative-test the *wrong scheme*, not just garbage input. (Caught 2026-09-05.)
- **A validated config field must be consumed.** parsed + exported + tested ≠ wired. Every knob needs a wiring regression test (config → the consumer it controls) or it's a silent no-op. (Caught 2026-09-05: `PG_MAX_CONNECTIONS`.)
- **Linter warnings are errors (rule 10), but linters exit 0 by default.** Biome prints "Found N warnings" yet exits 0, so a bare `biome check .` gate passes fixable issues. Gate on `biome check --error-on-warnings .` — in the project `lint` script AND in `ts-qc-check.sh`.
- **node-postgres `Pool` needs an `'error'` listener.** Idle clients emit `'error'` when the server restarts; with no listener it's an unhandled exception that crashes the process. Log, don't die. (Caught 2026-09-05.)
- **Biome 2.2+ config**: folder ignore is `files.includes: ["**", "!dir"]` — `files.ignore` is gone and `!dir/**` is deprecated (`useBiomeIgnoreFolder`). Pin `$schema` so the warnings-as-errors gate surfaces the deprecation.

### QC gate

`ts-qc-check.sh` (this skill) — run from any TS project root. Checks: pnpm build-approval sanity (placeholder + duplicate keys), placeholder literals in committed config, lockfile committed, the project gate `pnpm lint && pnpm typecheck && pnpm test`, then biome warnings-as-errors (`--error-on-warnings`), a `z.url()` scheme hint, and an engines↔mise drift warning. `SKIP_GATE=1` skips the lint/typecheck/test gate.

## Notes / intentionally deferred

- **Lockfiles, secret scanners**: deferred (not yet a problem here). Revisit if the
  toolchain grows or a secret actually leaks. (Git discipline: no longer deferred —
  see above.)
- Power-of-Ten rules 3 (no runtime allocation), 8 (limit metaprogramming), 9 (pointer
  indirection) are C/safety-critical concerns — **N/A** for these Python pipelines.
