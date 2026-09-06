#!/usr/bin/env bash
# bash-guard-check.sh — detect the silent-abort pattern that bit check_intel_monitor.sh.
#
# Under `set -euo pipefail`, a bare assignment `VAR=$( … grep … )` aborts the
# whole script when grep returns 1 (no match): pipefail makes the pipeline exit 1,
# the assignment inherits it, and `set -e` kills the script with no output and no
# log line — the report silently never fires.
#
# Fix idiom: guard the capture with `|| true` (or `|| echo ""`):
#     last_status=$(grep "# STATUS" "$f" 2>/dev/null | tail -1 || true)
#
# NOTE: `local x=$(grep …)` and `echo "$(grep …)"` MASK the failure (exit 0),
# so they don't abort — but they still silently drop the value. Prefer `|| true`.
#
# Usage:  bash-guard-check.sh [path...]     (default: *.sh under cwd)
# Exit:   0 = clean, 1 = unguarded pattern(s) found
set -uo pipefail

declare -a paths
if (($#)); then
  paths=("$@")
else
  mapfile -t paths < <(find . -name '*.sh' \
    -not -path '*/.venv*/*' -not -path '*/.git/*' 2>/dev/null || true)
fi

found=0
for f in "${paths[@]}"; do
  [ -f "$f" ] || continue
  # The abort only happens under errexit — check `set -e` or `set -o errexit`.
  grep -qE '(set[[:space:]]+-[a-zA-Z]*e[a-zA-Z]*([[:space:]]|$)|set[[:space:]]+-o[[:space:]]+errexit)' "$f" 2>/dev/null || continue

  while IFS= read -r hit; do
    lineno="${hit%%:*}"
    line="${hit#*:}"
    line_code="${line%%#*}"
    # A `||` outside comments means the pipeline is guarded (the `|| true` idiom).
    if ! printf '%s' "$line_code" | grep -q '||'; then
      printf '%s:%s: unguarded VAR=$(… grep …) under set -e → add "|| true"\n' "$f" "$lineno"
      found=1
    fi
  done < <(grep -nE '^[[:space:]]*(export[[:space:]]+|readonly[[:space:]]+|declare([[:space:]]+-[a-zA-Z]+)?[[:space:]]+)?[A-Za-z_][A-Za-z0-9_]*=\$\([^()]*\<grep\>' "$f" 2>/dev/null || true)
done

exit "$found"
