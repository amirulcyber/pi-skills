#!/usr/bin/env bash
# Dev gate — the mechanical layer (Power-of-Ten rule 10: zero static warnings).
# Reusable: run from any project root. ruff is pointed at this skill's config.
#
# Per-project knobs via env:
#   PY         python interpreter                     (default: .venv/bin/python if present, else python3)
#   SELFTEST   `python -c` snippet for contract self-test (default: none)
#   TEST_PY    python with pytest installed           (default: $PY)
#   PYRIGHT    pyright binary                         (default: .venv/bin/pyright if present, else none)
#
# Fails on: syntax, contract selftest, tests, ruff (incl. B018, BLE001, RUF100), pyright, bash grep-guard.
# Advises on: nasa-lsp (its assert-density rule is miscalibrated for scripts).
set -euo pipefail
SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PY="${PY:-$([ -x .venv/bin/python ] && echo .venv/bin/python || echo python3)}"
SELFTEST="${SELFTEST:-}"
TEST_PY="${TEST_PY:-$PY}"
PYRIGHT="${PYRIGHT:-$([ -x .venv/bin/pyright ] && echo .venv/bin/pyright || echo "")}"

echo "== 1/7 compile =="
# templates/ holds scaffolding that is deliberately not valid Python until it is
# copied and filled in (e.g. ai-security's `{category_name}_scorer.py` templates),
# so it must not be compiled. Same reason .venv and .git are excluded.
mapfile -t files < <(find . -name '*.py' \
  -not -path '*/.venv*/*' -not -path '*/.git/*' -not -path '*/__pycache__/*' \
  -not -path '*/templates/*' \
  2>/dev/null || true)
if ((${#files[@]})); then
  "$PY" -m py_compile "${files[@]}"
else
  echo "  (no .py files found — skipping)"
fi

echo "== 2/7 contract selftest =="
if [ -n "$SELFTEST" ]; then
  "$PY" -c "$SELFTEST"
else
  echo "  (SELFTEST not set — skipping)"
fi

echo "== 3/7 pytest =="
mapfile -t test_files < <(find . \( -name 'test_*.py' -o -name '*_test.py' \) \
  -not -path '*/.venv*/*' -not -path '*/.git/*' 2>/dev/null || true)
if ((${#test_files[@]})); then
  if "$TEST_PY" -m pytest --version >/dev/null 2>&1; then
    "$TEST_PY" -m pytest -q
  else
    echo "ERROR: test files found but pytest is not available in $TEST_PY" >&2
    exit 1
  fi
elif "$TEST_PY" -m pytest --version >/dev/null 2>&1; then
  "$TEST_PY" -m pytest -q
else
  echo "  (no test files found and pytest unavailable — skipping)"
fi

echo "== 4/7 ruff =="
uvx ruff@0.16.5 check --config "$SKILL_DIR/ruff.toml" .

echo "== 5/7 pyright =="
if [ -n "$PYRIGHT" ] && [ -x "$PYRIGHT" ] && ((${#files[@]})); then
  "$PYRIGHT" --pythonpath "$PY" "${files[@]}"
else
  echo "  (pyright not configured or unavailable — skipping)"
fi

echo "== 6/7 nasa-lsp (advisory) =="
uvx --from nasa-lsp nasa lint . || echo "  (advisory — see findings above)"

echo "== 7/7 bash guard =="
if ! "$SKILL_DIR/bash-guard-check.sh"; then
  echo "  (fix the unguarded VAR=\$(… grep …) patterns listed above)"
  exit 1
fi

echo "OK"
