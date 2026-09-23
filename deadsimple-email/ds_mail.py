#!/usr/bin/env python3
"""ds_mail.py — DeadSimple.email inbox ops (stdlib only, fail-loud).

Auth: DEADSIMPLE_API_KEY from .env next to this script (mode 600).
Base: https://api.deadsimple.email. All commands print JSON or short
lines; any HTTP error prints status + body to stderr and exits 1.
"""
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.parse

BASE = "https://api.deadsimple.email"
HERE = os.path.dirname(os.path.abspath(__file__))


def load_key() -> str:
    env = os.path.join(HERE, ".env")
    if not os.path.exists(env):
        raise SystemExit(".env missing (need DEADSIMPLE_API_KEY=...)")
    for line in open(env):
        line = line.strip()
        if line.startswith("DEADSIMPLE_API_KEY="):
            key = line.split("=", 1)[1].strip()
            if key:
                return key
    raise SystemExit("DEADSIMPLE_API_KEY not set in .env")


def unwrap(d):
    """API nests payloads under data:; accept both shapes."""
    if isinstance(d, dict) and isinstance(d.get("data"), dict):
        inner = d["data"]
        out = dict(inner)
        out.setdefault("meta", d.get("meta"))
        return out
    return d


def call(method, path, body=None, auth=True, key=""):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
    if auth:
        headers["Authorization"] = "Bearer " + key
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            raw = resp.read().decode("utf-8", "replace")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", "replace")[:500]
        print(f"HTTP {e.code} {method} {path}: {err}", file=sys.stderr)
        sys.exit(1)


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("health")
    p = sub.add_parser("create")
    p.add_argument("--prefix", default="agent")
    p = sub.add_parser("list")
    p.add_argument("--inbox", required=True)
    p.add_argument("--limit", type=int, default=10)
    p = sub.add_parser("read")
    p.add_argument("--inbox", required=True)
    p.add_argument("--msg", required=True)
    p.add_argument("--out", default="")
    p = sub.add_parser("send")
    p.add_argument("--inbox", required=True)
    p.add_argument("--to", required=True)
    p.add_argument("--subject", required=True)
    g = p.add_mutually_exclusive_group()
    g.add_argument("--text", default="")
    g.add_argument("--body-file", default="")
    p = sub.add_parser("reply")
    p.add_argument("--inbox", required=True)
    p.add_argument("--msg", required=True)
    p.add_argument("--text", required=True)
    p = sub.add_parser("poll")
    p.add_argument("--inbox", required=True)
    p.add_argument("--timeout", type=int, default=120)
    a = ap.parse_args()

    if a.cmd == "health":
        s, d = call("GET", "/v1/health", auth=False)
        print(json.dumps(d)[:300])
        return 0

    key = load_key()
    if a.cmd == "create":
        s, d = call("POST", "/v1/inboxes", {"name": a.prefix}, key=key)
        d = unwrap(d)
        print(json.dumps({k: d.get(k) for k in
                          ("inbox_id", "id", "address", "email") if d.get(k)}))
        return 0
    if a.cmd == "list":
        s, d = call("GET", f"/v1/inboxes/{a.inbox}/messages?"
                           f"{urllib.parse.urlencode({'limit': a.limit})}", key=key)
        d = unwrap(d)
        msgs = d.get("messages") or d.get("data") or []
        print(f"{len(msgs)} messages")
        for m in msgs:
            print(m.get("message_id") or m.get("id"), repr(m.get("subject")),
                  (m.get("from") or {}).get("address")
                  if isinstance(m.get("from"), dict) else m.get("from"))
        return 0
    if a.cmd == "read":
        s, d = call("GET", f"/v1/inboxes/{a.inbox}/messages/{a.msg}", key=key)
        out = json.dumps(d, indent=1)
        if a.out:
            open(a.out, "w").write(out)
            print(f"saved {a.out} ({len(out)} bytes)")
        else:
            print(out[:3000])
        return 0
    if a.cmd == "send":
        text = a.text or (open(a.body_file).read() if a.body_file else "")
        s, d = call("POST", f"/v1/inboxes/{a.inbox}/messages",
                    {"to": a.to, "subject": a.subject, "text_body": text}, key=key)
        print(f"sent HTTP {s}: {json.dumps(d)[:200]}")
        return 0
    if a.cmd == "reply":
        s, d = call("POST", f"/v1/inboxes/{a.inbox}/messages/{a.msg}/reply",
                    {"text_body": a.text}, key=key)
        print(f"replied HTTP {s}: {json.dumps(d)[:200]}")
        return 0
    if a.cmd == "poll":
        deadline = time.time() + a.timeout
        while time.time() < deadline:
            s, d = call("GET", f"/v1/inboxes/{a.inbox}/messages?limit=5", key=key)
            d = unwrap(d)
            msgs = d.get("messages") or d.get("data") or []
            if msgs:
                print(f"{len(msgs)} messages")
                for m in msgs:
                    print(m.get("message_id") or m.get("id"), repr(m.get("subject")))
                return 0
            time.sleep(10)
        print("0 messages (timeout)")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
