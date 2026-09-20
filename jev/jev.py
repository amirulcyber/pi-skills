"""JEV (TypeSafe System One) client — structured decisions, not chat.

Unstructured state in, typed calibrated decisions out. No text generation,
no hallucination surface: answers are choice/score/noul with probabilities.

Key rule: NON-PRIVILEGED DATA ONLY. Never send passwords, session cookies,
API keys, customer PII, mailbox contents with tokens, or any secret. Sanitize
states before calling (response shapes, verdicts, methodology — fine).

Usage:
    from jev import decide
    ans = decide("state text...", hit={"vulnerable": "...", "secure": "..."})
    # -> {"hit": {"choice": "secure", "probabilities": {...}, "confidence": ..}}

Env: TYPESAFE_BASE_URL + TYPESAFE_API_KEY from .env beside this file.
"""
import json
import os
import urllib.request

_HERE = os.path.dirname(os.path.abspath(__file__))


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


_ENV = _load_env()
BASE = os.environ.get("TYPESAFE_BASE_URL", _ENV.get("TYPESAFE_BASE_URL", "https://api.codiv.ai"))
KEY = os.environ.get("TYPESAFE_API_KEY", _ENV.get("TYPESAFE_API_KEY", ""))


def query(state, questions, model="openjev-latest", timeout=60):
    """Raw call. questions: {"name": {"type": "noul" |
    {"type": "choice", "criteria": {label: description}} |
    {"type": "score", "criteria": [level0..levelN (2-10)]}}}."""
    if not KEY:
        raise RuntimeError("TYPESAFE_API_KEY missing (.env or env)")
    body = json.dumps({"model": model, "state": state, "questions": questions}).encode()
    req = urllib.request.Request(
        BASE.rstrip("/") + "/v1/systemone", data=body,
        headers={"Authorization": "Bearer " + KEY, "Content-Type": "application/json",
                 "User-Agent": "pi-jevc/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)


def decide(state, model="openjev-latest", **criteria):
    """Decide one state against {label: description} choice criteria.
    Returns {"choice": label, "probabilities": {...}, "confidence": float}."""
    if len(criteria) < 2:
        raise ValueError("need >=2 choice labels")
    d = query(state, {"q": {"type": "choice", "criteria": criteria}}, model=model)
    return d["answers"]["q"]


def score(state, levels, model="openjev-latest"):
    """Score a state on 2-10 ordered levels. Returns full answer dict."""
    if not 2 <= len(levels) <= 10:
        raise ValueError("need 2-10 levels")
    d = query(state, {"q": {"type": "score", "criteria": levels}}, model=model)
    return d["answers"]["q"]


def null_prob(state, model="openjev-latest"):
    """noul baseline probability for a state. Returns float."""
    d = query(state, {"q": {"type": "noul"}}, model=model)
    return d["answers"]["q"]["noul"]


if __name__ == "__main__":
    import sys
    state = sys.argv[1] if len(sys.argv) > 1 else "smoke test state"
    print(json.dumps(decide(state,
        positive="the state indicates the tested action succeeded",
        negative="the state indicates the tested action was rejected"), indent=1))
