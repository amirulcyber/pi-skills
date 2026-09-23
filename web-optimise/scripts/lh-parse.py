#!/usr/bin/env python3
"""lh-parse.py — summarise a Lighthouse JSON report into an action list.

Usage: lh-parse.py <report.json> [--top N]

Stdlib only. Prints category scores, lab metrics, then every failing audit
(score < 0.9, or >=100 ms estimated savings) with savings and — for
image/contrast failures — the offending selectors/URLs.
"""
import json
import sys

METRICS = [
    "first-contentful-paint",
    "largest-contentful-paint",
    "total-blocking-time",
    "cumulative-layout-shift",
    "speed-index",
    "interactive",
]

NODE_AUDITS = {
    "color-contrast",
    "image-delivery-insight",
    "modern-image-formats",
    "properly-size-images",
    "offscreen-images",
    "uses-responsive-images",
}


def fmt_bytes(n):
    if n is None:
        return "-"
    n = float(n)
    for unit in ("B", "KiB", "MiB"):
        if n < 1024 or unit == "MiB":
            return f"{n:.0f} {unit}"
        n /= 1024
    return f"{n:.0f} MiB"


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__.strip().splitlines()[2])
        sys.exit(2)
    top = 5
    if "--top" in sys.argv:
        top = int(sys.argv[sys.argv.index("--top") + 1])

    with open(sys.argv[1], encoding="utf-8") as f:
        d = json.load(f)

    print(f"== {sys.argv[1]} ==")
    cats = d.get("categories", {})
    for k, v in cats.items():
        if k == "agentic-browsing":
            continue
        print(f"  {k}: {v.get('score')}")
    print("  -- metrics --")
    audits = d.get("audits", {})
    for m in METRICS:
        a = audits.get(m, {})
        print(f"  {m}: {a.get('displayValue', '-')} (score {a.get('score')})")
    print("  -- failing audits --")
    failed = 0
    for aid, a in audits.items():
        det = a.get("details", {}) if isinstance(a.get("details"), dict) else {}
        savings = det.get("overallSavingsMs", 0) or 0
        wasted = det.get("overallSavingsBytes", 0) or 0
        score = a.get("score")
        if (score is not None and score < 0.9) or savings >= 100:
            failed += 1
            print(
                f"  [{aid}] score={score} "
                f"savings={savings:.0f}ms/{fmt_bytes(wasted)} "
                f"val={a.get('displayValue', '-')!r} :: {a.get('title')}"
            )
            items = det.get("items", []) if isinstance(det, dict) else []
            for it in items[:top]:
                if aid in NODE_AUDITS:
                    node = it.get("node", {})
                    print(
                        f"    - {node.get('selector', it.get('url', '?'))} "
                        f"{(node.get('snippet') or '')[:120]}"
                    )
                elif "url" in it:
                    print(
                        f"    - {it['url'][:110]} "
                        f"total={fmt_bytes(it.get('totalBytes'))} "
                        f"wasted={fmt_bytes(it.get('wastedBytes'))}"
                    )
    if not failed:
        print("  (none — all audits pass)")
    srv = audits.get("server-response-time", {})
    print(f"  server-response-time: {srv.get('displayValue', '-')} "
          f"(re-run if this spikes: TTFB noise swings lab scores)")


if __name__ == "__main__":
    main()
