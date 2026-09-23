#!/usr/bin/env python3
"""Sample: add a Cronitor end-of-run heartbeat to ANY scheduled job.

Copy the heartbeat section into your job script — that's the whole pattern.
Rules baked in (see SKILL.md):
  1. Ping at the VERY END only: `complete` after everything succeeded,
     `/fail` on detected problems. A run that dies or hangs mid-way sends
     nothing, and Cronitor's grace window alerts on the missed ping.
  2. Use the TELEMETRY-ONLY ping key in pings — never the account API key
     (which can create/delete monitors). Ping key lives in .env here and is
     safe to embed: worst case a leaked URL fakes a heartbeat.
  3. Fail-ping before any notification I/O, so a hanging webhook can't
     block the failure signal.
  4. Never let the ping crash the job: network errors are swallowed.

Stdlib only. Demo: `python3 sample_heartbeat_job.py [--fail] [--crash]`
"""
from __future__ import annotations

import argparse
import sys
import urllib.error
import urllib.request

# --- heartbeat configuration (telemetry-only key, safe to embed) ----------
PING_KEY = "bef7372cd59645b6bb6d6544614e72e2"  # cronitor .env: CRONITOR_PING_KEY
MONITOR_CODE = "cIJGdE"  # 'kron-audit-hourly' — point new jobs at their own monitor
PING_BASE = "https://cronitor.link/p"
# --------------------------------------------------------------------------


def cronitor_ping(failed: bool, msg: str | None = None) -> None:
    """End-of-run heartbeat. Best-effort: never raises."""
    try:
        event = "fail" if failed else "complete"
        url = f"{PING_BASE}/{PING_KEY}/{MONITOR_CODE}/{event}"
        if msg:
            url += "?message=" + urllib.request.quote(msg)
        with urllib.request.urlopen(url, timeout=15) as r:  # noqa: S310
            if r.status >= 300:
                print(f"cronitor ping: HTTP {r.status}", file=sys.stderr)
    except OSError as e:
        print(f"cronitor ping failed (job continues): {e}", file=sys.stderr)


def do_work(fail: bool = False) -> None:
    """Your real job logic goes here."""
    if fail:
        raise RuntimeError("job detected a problem")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--fail", action="store_true", help="simulate a detected failure")
    ap.add_argument("--crash", action="store_true", help="simulate a mid-run crash")
    args = ap.parse_args()

    if args.crash:  # uncaught crash mid-run: no ping is sent at all
        raise RuntimeError("simulated mid-run crash")  # Cronitor alerts via grace
    try:
        do_work(fail=args.fail)  # a hang or SIGKILL here also sends nothing
        return 0                 # -> caught by Cronitor's grace window
    except Exception as e:  # noqa: BLE001 - crash must register as /fail
        print(f"job failed: {e}", file=sys.stderr)
        cronitor_ping(failed=True, msg=str(e))  # rule 3: before notify I/O
        return 1
    cronitor_ping(failed=False)  # rule 1: only after a fully successful run
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
