#!/usr/bin/env python3
"""am_mail.py — AgentMail inbox ops (stdlib only, fail-loud).

Auth: AGENTMAIL_API_KEY from .env next to this script (mode 600).
Base: https://api.agentmail.to (v0 paths). Mirrors ds_mail.py contract.
"""
import argparse
import json
import os
import sys
import time
import urllib.request
import urllib.parse

BASE = "https://api.agentmail.to"
HERE = os.path.dirname(os.path.abspath(__file__))


def q(s):
    """Path-segment quoting (message IDs contain <>/@)."""
    return urllib.parse.quote(str(s), safe="")


def load_key() -> str:
    env = os.path.join(HERE, ".env")
    if not os.path.exists(env):
        raise SystemExit(".env missing (need AGENTMAIL_API_KEY=...)")
    for line in open(env):
        line = line.strip()
        if line.startswith("AGENTMAIL_API_KEY="):
            key = line.split("=", 1)[1].strip()
            if key:
                return key
    raise SystemExit("AGENTMAIL_API_KEY not set in .env")


def call(method, path, body=None, key=""):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    headers = {"Accept": "application/json"}
    if body is not None:
        headers["Content-Type"] = "application/json"
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


def show(m):
    mid = m.get("message_id") or m.get("id")
    frm = m.get("from") or m.get("from_email") or m.get("sender") or ""
    if isinstance(frm, dict):
        frm = frm.get("address", "")
    print(mid, repr(m.get("subject")), frm)


def main() -> int:
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("create")
    p.add_argument("--name", default="agent")
    p = sub.add_parser("inboxes")
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
    key = load_key()

    if a.cmd == "create":
        s, d = call("POST", "/v0/inboxes", {"name": a.name}, key=key)
        print(json.dumps(d)[:400])
        return 0
    if a.cmd == "inboxes":
        s, d = call("GET", "/v0/inboxes", key=key)
        items = d if isinstance(d, list) else (d.get("inboxes") or d.get("data") or [])
        for ib in items:
            print(ib.get("inbox_id") or ib.get("id") or "?",
                  "|", ib.get("email") or ib.get("inbox") or "?",
                  "|", ib.get("created_at", ""))
        print(f"{len(items)} inbox(es)")
        return 0
    if a.cmd == "list":
        s, d = call("GET", f"/v0/inboxes/{a.inbox}/messages?"
                           f"{urllib.parse.urlencode({'limit': a.limit})}", key=key)
        msgs = d.get("messages") or d.get("data") or []
        print(f"{len(msgs)} messages")
        for m in msgs:
            show(m)
        return 0
    if a.cmd == "read":
        s, d = call("GET", f"/v0/inboxes/{a.inbox}/messages/{q(a.msg)}", key=key)
        out = json.dumps(d, indent=1)
        if a.out:
            open(a.out, "w").write(out)
            print(f"saved {a.out} ({len(out)} bytes)")
        else:
            print(out[:3000])
        return 0
    if a.cmd == "send":
        text = a.text or (open(a.body_file).read() if a.body_file else "")
        s, d = call("POST", f"/v0/inboxes/{a.inbox}/messages/send",
                    {"to": a.to, "subject": a.subject, "text": text}, key=key)
        print(f"sent HTTP {s}: {json.dumps(d)[:200]}")
        return 0
    if a.cmd == "reply":
        s, d = call("POST", f"/v0/inboxes/{a.inbox}/messages/{q(a.msg)}/reply",
                    {"text": a.text}, key=key)
        print(f"replied HTTP {s}: {json.dumps(d)[:200]}")
        return 0
    if a.cmd == "poll":
        deadline = time.time() + a.timeout
        while time.time() < deadline:
            s, d = call("GET", f"/v0/inboxes/{a.inbox}/messages?limit=5", key=key)
            msgs = d.get("messages") or d.get("data") or []
            if msgs:
                print(f"{len(msgs)} messages")
                for m in msgs:
                    show(m)
                return 0
            time.sleep(10)
        print("0 messages (timeout)")
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
