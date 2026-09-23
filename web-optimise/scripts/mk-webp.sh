#!/usr/bin/env bash
# mk-webp.sh — generate responsive WebP (+JPG fallback) siblings for images.
#
# Usage:
#   mk-webp.sh [--quality Q] [--rungs 800,1200] <img...>     # responsive rungs
#   mk-webp.sh --thumb [--quality Q] <img...>                # 320x180 card crop
#   mk-webp.sh --check
#
# Rungs: <stem>-800.webp + <stem>-1200.webp (shrink-only, never upscales).
# Thumbs: <stem>-320.webp + <stem>-320.jpg (320x180 cover-crop for ~160x90 boxes).
# Needs: ImageMagick `magick` with WebP delegate.
set -u

Q=75
RUNGS="800,1200"
THUMB=0

usage() { echo "usage: $0 [--quality Q] [--rungs 800,1200] [--thumb] <img...> | --check" >&2; exit 2; }

if [ "${1:-}" = "--check" ]; then
  rc=0
  command -v magick >/dev/null 2>&1 && echo "  ✅ magick: $(magick -version 2>/dev/null | head -1)" || { echo "  ❌ magick missing"; rc=1; }
  magick -list format 2>/dev/null | grep -q "WEBP.*rw" && echo "  ✅ webp delegate" || { echo "  ❌ webp delegate missing"; rc=1; }
  exit "$rc"
fi

while [ $# -gt 0 ]; do
  case "$1" in
    --quality) Q="$2"; shift 2 ;;
    --rungs) RUNGS="$2"; shift 2 ;;
    --thumb) THUMB=1; shift ;;
    -h|--help) usage ;;
    --*) echo "unknown flag: $1" >&2; usage ;;
    *) break ;;
  esac
done
[ $# -ge 1 ] || usage
command -v magick >/dev/null 2>&1 || { echo "mk-webp: magick not found" >&2; exit 1; }

for f in "$@"; do
  [ -f "$f" ] || { echo "mk-webp: skip missing $f" >&2; continue; }
  stem="${f%.*}"
  if [ "$THUMB" = 1 ]; then
    magick "$f" -resize 320x180^ -gravity center -extent 320x180 -quality "$Q" "${stem}-320.webp"
    magick "$f" -resize 320x180^ -gravity center -extent 320x180 -quality "$Q" "${stem}-320.jpg"
    echo "thumb: ${stem}-320.webp + ${stem}-320.jpg" >&2
  else
    IFS=',' read -ra WIDTHS <<< "$RUNGS"
    for w in "${WIDTHS[@]}"; do
      magick "$f" -resize "${w}x>" -quality "$Q" -define webp:method=6 "${stem}-${w}.webp"
      echo "rung: ${stem}-${w}.webp" >&2
    done
  fi
done
ls -lh "$@" 2>/dev/null | awk '{print $9, $5}' >&2
