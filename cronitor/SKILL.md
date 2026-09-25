---
name: cronitor
description: Dead-man's-switch heartbeats for scheduled jobs via Cronitor (saturn VM). Use when creating a monitor for a new cron/kron job, wiring a script's end-of-run ping, checking why a monitor alerted, or updating grace windows. Covers the ping-at-the-end-only rule, the API key location, and the live monitor inventory.
---

# Cronitor Heartbeats

Cron catches *failures*; Cronitor catches *silence*. Any scheduled job whose
death would otherwise be invisible (job runs inside the scheduler it monitors,
process killed mid-run, host reboot) gets a heartbeat monitor.

## Key & tooling

- `$SKILL_ROOT` in this file = this skill's directory. Its absolute value is
  per host (`/workspace/pi-skills` on neotokyo, `~/piworkspace/pi-skills` on
  saturn) — resolve the host from the marker-file table in `../AGENTS.md`
  (no `hostname` call needed). Never hardcode either path.
- API key: `$SKILL_ROOT/cronitor/.env` (`CRONITOR_API_KEY=...`,
  chmod 600, gitignored — management API only)
- Ping key: same file (`CRONITOR_PING_KEY=...`) — telemetry-only, used in
  ALL ping URLs; a leaked ping URL cannot manage monitors
- Helper: `$SKILL_ROOT/cronitor/cronitor_ping.py` (stdlib only;
  pings use the ping key, `get`/`create` use the API key)

```bash
S=$SKILL_ROOT/cronitor/cronitor_ping.py
$S ping cIJGdE                 # complete (success)
$S ping cIJGdE --fail          # failure event
$S ping cIJGdE --msg "why it failed"
$S get cIJGdE                  # inspect monitor state
$S create <code> --name "..." --grace 1200 --note "..."
```

## Reference integration script

`sample_heartbeat_job.py` in this folder — a copy-paste template for wiring
any job with the end-of-run heartbeat (ping key embedded, crash/fail/success
paths demoed: `python3 sample_heartbeat_job.py [--fail|--crash]`). Start new
integrations from it, not from scratch.

## The rules (each traces to an incident)

1. **Ping at the very END of the run only.** `complete` after everything
   finished; `/fail` on detected problems. A process that dies or hangs
   mid-run sends nothing — Cronitor's grace window then alerts on the missed
   ping. (2026-09-20: kron daemon died silently; nothing noticed for 3 days.)
2. **The monitor of a scheduler must not run inside that scheduler.**
   kron-audit lives in johnn's user crontab, not in kron, so it can report
   kron's death. Same principle anywhere: watchdog ≠ watchdogged.
3. **Fail-ping before any notification I/O.** A hanging ntfy/webhook call
   must not block the `/fail` ping.
4. **Grace ≈ 1/3 of the interval** (hourly job → ~1200 s). Too short = alert
   noise on slow runs; too long = late detection.
5. **Best-effort sends**: ping helpers must exit non-zero on network errors,
   but callers wrap them so a Cronitor outage never breaks the real job.

## Live monitor inventory (saturn)

| Code | Monitor | Cadence | Pinger |
|---|---|---|---|
| `cIJGdE` | kron-audit-hourly | hourly :15 UTC | `kron_audit.py` (user crontab, out of kron) |

New monitors: `$S create <code> --name ... --grace ...`, then wire the
end-of-run ping into the job script, then verify once with `$S get <code>`
(`initialized: true`, latest_event matches). Also confirm the Cronitor
account has an alert target (dashboard → Notifications).

## Integration pattern (Python, stdlib)

```python
def cronitor_ping(failed: bool) -> None:
    # key from CRONITOR_KEY env or $SKILL_ROOT/cronitor/.env
    ...
```

Reference implementation: `mydashboard/scripts/kron_audit.py::cronitor_ping`
— env var first, skill `.env` fallback, end-of-run only, `/fail` on crash
via top-level try/except in `main()`.
