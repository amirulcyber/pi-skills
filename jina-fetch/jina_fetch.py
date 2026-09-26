#!/usr/bin/env python3
"""Fetch or search through Jina, resolving the key from the project .env.

    jina_fetch.py read <url>          rendered markdown of a URL
    jina_fetch.py read <url> --html   rendered DOM instead of markdown
    jina_fetch.py search "<query>"    grounded search results
    jina_fetch.py check               verify the key and show balance

The key is read from the project .env, never from argv, so it does not land in
a shell history or a process listing. It is never printed.

Exit codes: 0 ok, 1 no key, 2 empty body (a fetch that returned nothing is
reported as a failure, because a 200 with an empty body is not a read).
"""
import json
import os
import pathlib
import sys
import urllib.error
import urllib.request

# The response is a short header block then the body. Measuring the whole
# response makes an empty fetch look like a short page, so split on this.
MARKER = "Markdown Content:"


def find_env(explicit=None):
    """Locate a .env holding JINA_API_KEY, walking up from cwd."""
    cands = [pathlib.Path(explicit)] if explicit else []
    cands += [pathlib.Path(os.environ.get("JINA_ENV", "") or ".") / ".env"]
    here = pathlib.Path.cwd().resolve()
    cands += [p / ".env" for p in [here, *here.parents]]
    for c in cands:
        try:
            if c.is_file() and "JINA_API_KEY=" in c.read_text():
                return c
        except OSError:
            continue
    return None


def load_key():
    k = os.environ.get("JINA_API_KEY")
    if k:
        return k, "environment"
    p = find_env()
    if not p:
        return None, None
    for line in p.read_text().splitlines():
        line = line.strip()
        if line.startswith("JINA_API_KEY="):
            v = line.split("=", 1)[1].strip().strip("'\"")
            return (v or None), str(p)
    return None, str(p)


def body_of(text):
    """Return just the content, so an empty fetch is visible as empty."""
    return text.split(MARKER, 1)[1].strip() if MARKER in text else text.strip()


def req(url, headers, data=None, timeout=90):
    try:
        r = urllib.request.Request(url, data=data, headers=headers)
        with urllib.request.urlopen(r, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace")[:300]
    except Exception as e:                                        # noqa: BLE001
        return 0, f"{type(e).__name__}: {str(e)[:160]}"


def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return 1
    cmd = sys.argv[1]
    key, src = load_key()
    if not key:
        print("JINA_API_KEY not set. Add it to the project .env "
              "(mode 600, gitignored) or export it.", file=sys.stderr)
        return 1
    auth = {"Authorization": f"Bearer {key}"}

    if cmd == "check":
        # example.com is genuinely ~150 chars, so it cannot distinguish a working
        # key from a silently empty render. Probe a page that is always large.
        st, body = req("https://r.jina.ai/https://en.wikipedia.org/wiki/Main_Page", auth)
        c = len(body_of(body))
        print(f"key from: {src}")
        print(f"reader:   HTTP {st}, {c} chars of content")
        if c < 300:
            print("  <-- empty render: key may be invalid, or the reader is "
                  "being blocked. Try search, or a browser.", file=sys.stderr)
            return 2
        return 0

    if cmd == "read":
        url = sys.argv[2]
        h = dict(auth)
        h["X-Return-Format"] = "html" if "--html" in sys.argv else "markdown"
        h["X-Timeout"] = "30"
        st, body = req("https://r.jina.ai/" + url, h)
        content = body if h["X-Return-Format"] == "html" else body_of(body)
        print(content)
        if st != 200:
            return 2
        if len(content.strip()) < 300:
            # HackerOne and Google Bug Hunters both land here. Escalate to a
            # browser or an API rather than re-running this.
            print(f"\n[warn] HTTP {st} but {len(content.strip())} chars of content. "
                  "This page did not render; use a browser or the site API.",
                  file=sys.stderr)
            return 2
        return 0

    if cmd == "search":
        q = " ".join(sys.argv[2:])
        h = dict(auth, **{"Content-Type": "application/json",
                          "Accept": "application/json"})
        st, body = req("https://s.jina.ai/search", h,
                       json.dumps({"q": q}).encode())
        if st != 200:
            print(f"HTTP {st}: {body[:200]}", file=sys.stderr)
            return 2
        d = json.loads(body)
        for i, r in enumerate(d.get("data", []), 1):
            print(f"{i}. {r.get('title') or '(untitled)'}")
            print(f"   {r.get('url')}")
            if r.get("description"):
                print(f"   {r['description']}")
        return 0

    print(f"unknown command: {cmd}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
