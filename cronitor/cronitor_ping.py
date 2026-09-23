#!/usr/bin/env python3
"""Cronitor heartbeat/API helper — stdlib only.

Ping dead-man's-switch heartbeats and manage Cronitor monitors from the CLI.
The API key is resolved in this order (first hit wins):

  1. --key flag
  2. CRONITOR_KEY env var
  3. .env file (default: alongside this script, override with --env-file)

Usage:
  cronitor_ping.py ping <code> [--fail] [--msg S]     # heartbeat event
  cronitor_ping.py get <code>                         # fetch monitor JSON
  cronitor_ping.py create <code> --name N --grace S [--note S]

Ping semantics (heartbeat monitors):
  - ping ONLY at the very end of a run: `complete` on success, `/fail` on
    failure. A process that dies or hangs mid-run sends nothing, which
    Cronitor catches via the grace window (missed-ping alert).
  - never let the ping crash the caller: network errors exit non-zero here,
    but callers should treat ping failure as best-effort.

Exit codes: 0 = ping/API call succeeded, 1 = failed (reason on stderr).
  cronitor_ping.py [--key K] [--env-file P] <command> ...
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

API_BASE = "https://cronitor.io/api/monitors"
PING_BASE = "https://cronitor.link/p"
DEFAULT_ENV_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".env")
TIMEOUT = 15


def _read_env(path: str) -> dict[str, str]:
    """Parse KEY=VALUE lines from a dotenv-style file. Missing file is fine."""
    out: dict[str, str] = {}
    try:
        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                out[k.strip()] = v.strip().strip("'\"")
    except OSError:
        pass
    return out


def load_env_key(env_file: str = DEFAULT_ENV_FILE) -> dict[str, str]:
    return _read_env(env_file)


def resolve_keys(args: argparse.Namespace) -> tuple[str, str]:
    """Return (api_key, ping_key). Pings MUST use the ping key (telemetry-
    only); the API key is for management calls (get/create) exclusively."""
    file_cfg = load_env_key(args.env_file)
    api = args.key or os.environ.get("CRONITOR_API_KEY") or \
        file_cfg.get("CRONITOR_API_KEY", "")
    ping = args.ping_key or os.environ.get("CRONITOR_PING_KEY") or \
        file_cfg.get("CRONITOR_PING_KEY", "")
    return api, ping


def resolve_key(args: argparse.Namespace) -> str:
    api, _ = resolve_keys(args)
    if not api:
        print("cronitor: no API key (--key / CRONITOR_API_KEY / .env)",
              file=sys.stderr)
        raise SystemExit(1)
    return api


def _auth(key: str) -> str:
    import base64
    return "Basic " + base64.b64encode(f"{key}:".encode()).decode()


def _get(url: str, key: str) -> dict:
    req = urllib.request.Request(url)  # noqa: S310 - https, fixed hosts
    req.add_header("Authorization", _auth(key))
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:  # noqa: S310
        return json.loads(r.read().decode())


def _put(url: str, key: str, payload: dict) -> dict:
    req = urllib.request.Request(  # noqa: S310 - https, fixed hosts
        url, data=json.dumps(payload).encode(), method="PUT",
        headers={"Content-Type": "application/json",
                 "Authorization": _auth(key)})
    with urllib.request.urlopen(req, timeout=TIMEOUT) as r:  # noqa: S310
        return json.loads(r.read().decode())


def cmd_ping(args: argparse.Namespace) -> int:
    _, ping_key = resolve_keys(args)
    if not ping_key:
        print("cronitor: no ping key (--ping-key / CRONITOR_PING_KEY / .env)",
              file=sys.stderr)
        return 1
    event = "fail" if args.fail else "complete"
    url = f"{PING_BASE}/{ping_key}/{args.code}/{event}"
    if args.msg:
        url += "?message=" + urllib.request.quote(args.msg)
    try:
        with urllib.request.urlopen(url, timeout=TIMEOUT) as r:  # noqa: S310
            if r.status >= 300:
                print(f"cronitor ping {event}: HTTP {r.status}", file=sys.stderr)
                return 1
    except urllib.error.URLError as e:
        print(f"cronitor ping {event} failed: {e}", file=sys.stderr)
        return 1
    return 0


def cmd_get(args: argparse.Namespace) -> int:
    key = resolve_key(args)
    try:
        data = _get(f"{API_BASE}/{args.code}", key)
    except (urllib.error.URLError, OSError) as e:
        print(f"cronitor get failed: {e}", file=sys.stderr)
        return 1
    a = data  # Cronitor returns monitor fields top-level; attributes is a stub
    print(json.dumps({"code": a.get("code") or a.get("attributes", {}).get("code"),
                      "name": a.get("name"),
                      "type": a.get("type"), "grace_seconds": a.get("grace_seconds"),
                      "passing": a.get("passing"), "initialized": a.get("initialized"),
                      "latest_event": a.get("latest_event")}, indent=2))
    return 0


def cmd_create(args: argparse.Namespace) -> int:
    key = resolve_key(args)
    payload: dict = {"name": args.name, "type": "heartbeat"}
    if args.grace is not None:
        payload["grace_seconds"] = args.grace
    if args.note:
        payload["note"] = args.note
    try:
        data = _put(f"{API_BASE}/{args.code}", key, payload)
    except (urllib.error.URLError, OSError) as e:
        print(f"cronitor create failed: {e}", file=sys.stderr)
        return 1
    print(f"created: code={data['attributes']['code']} "
          f"grace={data['attributes']['grace_seconds']}s")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Cronitor heartbeat/API helper")
    ap.add_argument("--key", help="API key (management calls; else CRONITOR_API_KEY env, else .env)")
    ap.add_argument("--ping-key", help="ping key (telemetry; else CRONITOR_PING_KEY env, else .env)")
    ap.add_argument("--env-file", default=DEFAULT_ENV_FILE,
                    help=f"dotenv file with keys (default: {DEFAULT_ENV_FILE})")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("ping", help="send a heartbeat event")
    p.add_argument("code", help="monitor code (e.g. cIJGdE)")
    p.add_argument("--fail", action="store_true", help="send /fail instead of complete")
    p.add_argument("--msg", help="optional message attached to the ping")
    p.set_defaults(fn=cmd_ping)

    p = sub.add_parser("get", help="fetch one monitor")
    p.add_argument("code")
    p.set_defaults(fn=cmd_get)

    p = sub.add_parser("create", help="create/update a heartbeat monitor")
    p.add_argument("code", help="monitor code/key")
    p.add_argument("--name", required=True)
    p.add_argument("--grace", type=int, default=None, help="grace seconds")
    p.add_argument("--note", default=None)
    p.set_defaults(fn=cmd_create)

    args = ap.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())
