"""CapMonsterCloud solver client (paid, owner-authorized).

SCOPE: pass automation gates ONLY, to continue recon/vuln testing on
authorized engagements. FORBIDDEN: brute-force credential attacks,
claiming gate-passage as a bypass finding. EVERY use is logged with a
timestamp in the engagement triage log, with the note that the gate
cannot be passed without the solver.

Key: .env beside this file (600, gitignored). Never print it, never commit.
Docs: https://capmonster.cloud/docs ; repo: CapMonsterCloud on GitHub.
"""
import json
import os
import time
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))
_API = "https://api.capmonster.cloud"


def _load_env():
    cfg = {}
    try:
        with open(os.path.join(_HERE, ".env")) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    cfg[k.strip()] = v.strip()
    except FileNotFoundError:
        pass
    return cfg


_KEY = os.environ.get("CAPMONSTER_API_KEY", _load_env().get("CAPMONSTER_API_KEY", ""))


def _post(path, payload, timeout=30):
    if not _KEY:
        raise RuntimeError("CAPMONSTER_API_KEY missing (.env or env)")
    body = json.dumps(payload).encode()
    req = urllib.request.Request(
        _API + path, data=body,
        headers={"Content-Type": "application/json", "User-Agent": "pi-capmonster/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def get_balance():
    """Non-invasive key/balance check. Returns float USD."""
    d = _post("/getBalance", {"clientKey": _KEY})
    if d.get("errorId"):
        raise RuntimeError(f"capmonster: {d.get('errorCode')} {d.get('errorDescription')}")
    return float(d["balance"])


def create_task(task):
    """Create a solving task. task e.g.:
    {"type":"RecaptchaV2TaskProxyless","websiteURL":u,"websiteKey":k} or
    {"type":"RecaptchaV3TaskProxyless","websiteURL":u,"websiteKey":k,
     "minScore":0.3,"pageAction":"action"}. Returns taskId (int)."""
    d = _post("/createTask", {"clientKey": _KEY, "task": task})
    if d.get("errorId"):
        raise RuntimeError(f"capmonster: {d.get('errorCode')} {d.get('errorDescription')}")
    return int(d["taskId"])


def get_result(task_id, timeout=30):
    """Single poll. Returns (status, solution|None, raw)."""
    d = _post("/getTaskResult", {"clientKey": _KEY, "taskId": task_id})
    if d.get("errorId"):
        raise RuntimeError(f"capmonster: {d.get('errorCode')} {d.get('errorDescription')}")
    return d.get("status"), (d.get("solution") or {}).get("gRecaptchaResponse"), d


def solve(task, poll_interval=5, max_wait=180, spend_cap_usd=0.50):
    """Create + poll until ready. Returns gRecaptchaResponse token.
    spend_cap_usd: abort if reported price exceeds cap (when provided)."""
    tid = create_task(task)
    t0 = time.time()
    while time.time() - t0 < max_wait:
        time.sleep(poll_interval)
        status, token, raw = get_result(tid)
        if status == "ready":
            price = None
            try:
                price = float((raw.get("cost") or "0").split(":")[0])
            except Exception:
                pass
            if price is not None and price > spend_cap_usd:
                raise RuntimeError(f"solve cost {price} exceeds cap {spend_cap_usd}")
            return token
    raise TimeoutError(f"task {tid} not ready after {max_wait}s")


if __name__ == "__main__":
    print(f"balance: ${get_balance():.4f}")
