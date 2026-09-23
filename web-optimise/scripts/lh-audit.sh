#!/usr/bin/env bash
# lh-audit.sh — run mobile + desktop Lighthouse against live URL(s) using a
# local Chromium. No PageSpeed API quota involved.
#
# Usage:
#   lh-audit.sh [--out DIR] [--work DIR] [--chrome PATH] <url> [url...]
#   lh-audit.sh --check
#
# Output: <out>/<slug>-mobile.json, <out>/<slug>-desktop.json per URL.
# Needs: node/npx, network access to npm (first run installs lighthouse
# into --work), and a Chromium: --chrome, $CHROME_PATH, Playwright cache
# (~/.cache/ms-playwright), or system chrome/chromium on PATH.
set -u

OUT="/tmp/lh-out"
WORK="/tmp/lh-work"
CHROME="${CHROME_PATH:-}"

usage() {
  echo "usage: $0 [--out DIR] [--work DIR] [--chrome PATH] <url> [url...] | --check" >&2
  exit 2
}

if [ "${1:-}" = "--check" ]; then
  rc=0
  command -v node >/dev/null 2>&1 && echo "  ✅ node: $(node --version)" || { echo "  ❌ node missing"; rc=1; }
  command -v npx >/dev/null 2>&1 && echo "  ✅ npx present" || { echo "  ❌ npx missing"; rc=1; }
  if [ -n "$CHROME" ] && [ -x "$CHROME" ]; then
    echo "  ✅ chrome (CHROME_PATH): $CHROME"
  else
    found=""
    for c in "$HOME/.cache/ms-playwright/chromium-"*/chrome-linux/chrome \
             "$HOME"/.cache/ms-playwright/chromium_headless_shell-*/chrome-*/headless_shell \
             "$HOME"/.cache/ms-playwright/chromium_headless_shell-*/chrome-*/chrome-headless-shell; do
      if [ -x "$c" ]; then found="$c"; break; fi
    done
    if [ -z "$found" ]; then found="$(command -v chromium || command -v chromium-browser || command -v google-chrome || command -v google-chrome-stable || true)"; fi
    if [ -n "$found" ]; then echo "  ✅ chrome: $found"; else echo "  ❌ no chromium found (set --chrome or CHROME_PATH)"; rc=1; fi
  fi
  exit "$rc"
fi

while [ $# -gt 1 ]; do
  case "$1" in
    --out) OUT="$2"; shift 2 ;;
    --work) WORK="$2"; shift 2 ;;
    --chrome) CHROME="$2"; shift 2 ;;
    -h|--help) usage ;;
    --*) echo "unknown flag: $1" >&2; usage ;;
    *) break ;;
  esac
done
[ $# -ge 1 ] || usage

if [ -z "$CHROME" ]; then
  for c in "$HOME/.cache/ms-playwright/chromium-"*/chrome-linux/chrome \
           "$HOME"/.cache/ms-playwright/chromium_headless_shell-*/chrome-*/headless_shell \
           "$HOME"/.cache/ms-playwright/chromium_headless_shell-*/chrome-*/chrome-headless-shell; do
    if [ -x "$c" ]; then CHROME="$c"; break; fi
  done
  if [ -z "$CHROME" ]; then CHROME="$(command -v chromium || command -v chromium-browser || command -v google-chrome || command -v google-chrome-stable || true)"; fi
fi
if [ -z "$CHROME" ] || [ ! -x "$CHROME" ]; then
  echo "lh-audit: no working chromium (checked CHROME_PATH, Playwright cache, PATH)." >&2
  exit 1
fi

mkdir -p "$WORK" "$OUT"
if [ ! -x "$WORK/node_modules/.bin/lighthouse" ]; then
  echo "lh-audit: installing lighthouse into $WORK ..." >&2
  (cd "$WORK" && npm init -y >/dev/null 2>&1 && npm i lighthouse --no-audit --no-fund 2>&1 | tail -1 >&2)
fi
LH="$WORK/node_modules/.bin/lighthouse"
[ -x "$LH" ] || { echo "lh-audit: lighthouse install failed" >&2; exit 1; }

slugify() {
  echo "$1" | sed -e 's#^https\?://##' -e 's#[^A-Za-z0-9]\+#-#g' -e 's#^-##' -e 's#-$##' | cut -c1-80
}

export CHROME_PATH="$CHROME"
rc=0
for url in "$@"; do
  slug="$(slugify "$url")"
  echo "lh-audit: mobile  $url" >&2
  "$LH" "$url" --output=json --output-path="$OUT/$slug-mobile.json" \
    --chrome-flags="--no-sandbox --headless --disable-gpu" --quiet \
    --form-factor=mobile --screenEmulation.mobile=true || rc=1
  echo "lh-audit: desktop $url" >&2
  "$LH" "$url" --preset=desktop --output=json --output-path="$OUT/$slug-desktop.json" \
    --chrome-flags="--no-sandbox --headless --disable-gpu" --quiet || rc=1
done
echo "lh-audit: JSON in $OUT" >&2
exit "$rc"
