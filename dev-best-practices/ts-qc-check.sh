#!/usr/bin/env bash
# ts-qc-check.sh — TypeScript/Node/pnpm quality gate (dev-best-practices skill).
#
# Captures the classes that bit ts-ps-app (2026-09-05):
#   1. pnpm 11 auto-edits pnpm-workspace.yaml during `pnpm install`/`rebuild`,
#      injecting a placeholder `allowBuilds` value ("set this to true or false")
#      — the literal instruction string shipped in a commit.
#   2. Two build-approval keys (allowBuilds + onlyBuiltDependencies) = two sources
#      of truth; pnpm 11 superseded the latter.
#   3. Placeholder literals in committed config (changeme / example.com / <...> /
#      your-… / "not implemented").
#   4. Uncommitted pnpm-lock.yaml (CI runs `pnpm install --frozen-lockfile`).
#   5. Linter warnings passing the gate (Biome exits 0 on warnings — rule 10).
#   6. z.url() accepting any scheme while the error message claims a specific one.
#   7. engines.node drifting from the mise.toml pin.
#   8. `//` comments in strict-JSON config (biome.json) — JSON has no comments,
#      so the comment crashed the whole gate at parse time. Rationale lives in
#      the README, never in the JSON. (tsconfig*.json are JSONC — exempt.)
#   9. A standalone vitest.config.ts silently replacing vite.config.ts — vitest
#      loads ONE config, so plugins/aliases ($lib) vanish and tests die with
#      "Cannot find module". Vitest configs must mergeConfig the app config.
#
# Usage:  ts-qc-check.sh [project-root]   (default: cwd)
# Env:    SKIP_GATE=1  skip the pnpm lint/typecheck/test gate
# Exit:   0 = clean, 1 = fix required
set -euo pipefail

ROOT="${1:-.}"
cd "$ROOT"

fail=0
warn=0
say() { printf '%s\n' "$*"; }

# ------------------------------------------------------------ 1. build-approval config
WS=pnpm-workspace.yaml
if [ -f "$WS" ]; then
  # tool-injected placeholder value (pnpm 11 writes this literal into allowBuilds)
  if grep -nE 'set this to (true|false)' "$WS" >/dev/null; then
    say "FAIL: $WS contains a tool-injected placeholder (\"set this to true or false\") — replace with a real boolean"
    grep -nE 'set this to (true|false)' "$WS" | sed 's/^/    /'
    fail=$((fail + 1))
  fi
  # conflicting build-approval keys
  if grep -qE '^[[:space:]]*allowBuilds:' "$WS" && grep -qE '^[[:space:]]*onlyBuiltDependencies:' "$WS"; then
    say "FAIL: $WS defines both 'allowBuilds' and 'onlyBuiltDependencies' (pnpm 11 superseded the latter) — keep only 'allowBuilds'"
    fail=$((fail + 1))
  fi
fi

# ------------------------------------------------------------ 2. placeholder literals in config
declare -a cfgs=(package.json pnpm-workspace.yaml biome.json tsconfig.base.json mise.toml .mise.toml)
while IFS= read -r f; do cfgs+=("$f"); done \
  < <(find . -name 'tsconfig*.json' -not -path './node_modules/*' 2>/dev/null || true)
while IFS= read -r f; do cfgs+=("$f"); done \
  < <(find .github -type f \( -name '*.yml' -o -name '*.yaml' \) 2>/dev/null || true)

pat='changeme|change-me|example\.(com|org)|your-(org|token|repo|app)|placeholder|<[a-z0-9_-]+>|not implemented'
for f in "${cfgs[@]}"; do
  [ -f "$f" ] || continue
  if grep -nEi "$pat" "$f" >/dev/null; then
    say "FAIL: placeholder literal in $f"
    grep -nEi "$pat" "$f" | sed 's/^/    /'
    fail=$((fail + 1))
  fi
  if grep -nEi '\b(TODO|FIXME)\b' "$f" >/dev/null; then
    say "WARN: TODO/FIXME marker in $f (review before merge)"
    warn=$((warn + 1))
  fi
done

# ------------------------------------------------------------ 3. lockfile committed
if [ -f package.json ]; then
  if [ ! -f pnpm-lock.yaml ]; then
    say "FAIL: pnpm-lock.yaml missing — CI runs 'pnpm install --frozen-lockfile'"
    fail=$((fail + 1))
  else
    if grep -qE '(^|/)pnpm-lock\.yaml$' .gitignore 2>/dev/null; then
      say "FAIL: .gitignore excludes pnpm-lock.yaml — it must be committed"
      fail=$((fail + 1))
    fi
    if [ -d .git ] && ! git ls-files --error-unmatch pnpm-lock.yaml >/dev/null 2>&1; then
      say "WARN: pnpm-lock.yaml is untracked — commit it"
      warn=$((warn + 1))
    fi
  fi
fi

# ------------------------------------------------------------ 4. lint + typecheck + test
if [ "${SKIP_GATE:-0}" = "1" ]; then
  say "SKIP: gate (SKIP_GATE=1)"
elif command -v pnpm >/dev/null 2>&1; then
  # `if cmd1 && cmd2 && cmd3` — NOT a bare `cmd1 && cmd2 && cmd3`: under
  # set -e a non-final command in an && list never triggers errexit, so a
  # failing lint would silently fall through to "RESULT: OK" (caught by the
  # tool's own negative test, 2026-09-05).
  if pnpm lint && pnpm typecheck && pnpm test; then
    :
  else
    say "FAIL: gate (pnpm lint && pnpm typecheck && pnpm test)"
    fail=$((fail + 1))
  fi
else
  say "WARN: pnpm not on PATH — run 'pnpm lint && pnpm typecheck && pnpm test' manually"
  warn=$((warn + 1))
fi

# ------------------------------------------------------------ 5. linter warnings must fail (rule 10)
# Biome exits 0 with warning diagnostics, so a gate built on a bare
# `biome check .` silently passes "fixable" issues (e.g. useBiomeIgnoreFolder).
# Gate on warnings-as-errors regardless of what the project's lint script does.
if { [ -f biome.json ] || [ -f biome.jsonc ]; } && command -v pnpm >/dev/null 2>&1; then
  if pnpm exec biome check --error-on-warnings . >/dev/null 2>&1; then
    :
  else
    say "FAIL: biome warnings/errors — linter warnings are errors; run 'biome check --error-on-warnings .'"
    fail=$((fail + 1))
  fi
fi

# ------------------------------------------------------------ 6. validator must enforce what its message claims
# z.url() accepts ANY URL scheme (http://, mysql:// …). If a config field's error
# message claims a specific scheme (e.g. "postgres connection string"), enforce it
# with .refine()/.regex() — otherwise a wrong scheme passes validation and only
# blows up at first connect. WARN (a legitimate generic-URL validator exists).
if grep -rEn 'z\.url\(' --include='*.ts' --exclude-dir=node_modules . >/dev/null 2>&1; then
  say "WARN: z.url() accepts any URL scheme — if the value must be a specific scheme (postgres:// etc.), enforce it with .refine()/.regex()"
  grep -rEn 'z\.url\(' --include='*.ts' --exclude-dir=node_modules . | sed 's/^/    /'
  warn=$((warn + 1))
fi

# ------------------------------------------------------------ 7. engines.node must match the toolchain pin
# A loose `>=22` next to a mise pin of 24.20.0 is drift: CI (mise) runs one Node,
# developers assuming a bare `>=22` run another. Warn on mismatch.
if [ -f package.json ]; then
  for mf in mise.toml .mise.toml; do
    [ -f "$mf" ] || continue
    mise_node="$(sed -nE 's/^[[:space:]]*node[[:space:]]*=[[:space:]]*"([0-9]+\.[0-9]+).*/\1/p' "$mf" | head -1)"
    if [ -n "$mise_node" ] && ! grep -qE "\"node\"[[:space:]]*:[[:space:]]*\"[^\"]*${mise_node}" package.json; then
      say "WARN: $mf pins node ${mise_node} but package.json engines.node doesn't include it (drift)"
      warn=$((warn + 1))
    fi
  done
fi

# ------------------------------------------------------------ 8. strict-JSON configs must parse
# biome.json / package.json are strict JSON — a `//` comment anywhere in them
# kills every consumer at parse time (the whole gate crashed on this).
# tsconfig*.json are JSONC (comments legal for tsc) and are exempt.
if command -v node >/dev/null 2>&1; then
  for jf in biome.json biome.jsonc package.json components.json; do
    [ -f "$jf" ] || continue
    case "$jf" in
      *.jsonc) continue ;;
    esac
    if ! _QC_JSON="$jf" node -e "JSON.parse(require('fs').readFileSync(process.env._QC_JSON,'utf8'))" 2>/dev/null; then
      say "FAIL: $jf is not valid strict JSON (JSON has no comments — put rationale in the README)"
      fail=$((fail + 1))
    fi
  done
else
  say "WARN: node not on PATH — skipping strict-JSON check"
  warn=$((warn + 1))
fi

# ------------------------------------------------------------ 9. vitest configs must merge the app vite config
# Vitest loads a single config file: a standalone vitest.config.ts REPLACES
# vite.config.ts, silently dropping plugins and aliases ($lib vanished and
# every test died with "Cannot find module"). Each vitest config sitting next
# to a vite.config.ts must merge it (mergeConfig + import of ./vite.config).
while IFS= read -r vf; do
  dir="$(dirname "$vf")"
  if [ -f "$dir/vite.config.ts" ] && ! grep -qE 'mergeConfig|vite\.config' "$vf"; then
    say "FAIL: $vf sits next to $dir/vite.config.ts but does not merge it — vitest will drop vite plugins/aliases"
    fail=$((fail + 1))
  fi
done < <(find . -name 'vitest*.config.ts' -not -path '*/node_modules/*' 2>/dev/null || true)

# ------------------------------------------------------------ report
if [ "$fail" -ne 0 ]; then
  say "RESULT: FAIL ($fail issue(s) to fix)"
  exit 1
fi
if [ "$warn" -ne 0 ]; then
  say "RESULT: OK with warnings ($warn)"
else
  say "RESULT: OK"
fi
