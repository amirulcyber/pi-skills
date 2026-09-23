#!/usr/bin/env python3
"""contrast.py — WCAG 2.x contrast ratio for foreground/background hex pairs.

Usage: contrast.py <fg> <bg> [<fg2> <bg2> ...] | --check

PASS needs >= 4.5:1 (AA normal text); >= 3.0:1 passes AA-large only.
Stdlib only.
"""
import sys


def lum(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    r, g, b = (int(h[i : i + 2], 16) / 255 for i in (0, 2, 4))

    def f(c):
        return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

    r, g, b = f(r), f(g), f(b)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def ratio(fg, bg):
    l1, l2 = lum(fg), lum(bg)
    return (max(l1, l2) + 0.05) / (min(l1, l2) + 0.05)


def verdict(r):
    if r >= 4.5:
        return "PASS (AA)"
    if r >= 3.0:
        return "FAIL body / PASS large-only"
    return "FAIL"


def main():
    if sys.argv[1:] == ["--check"]:
        print("contrast.py OK (stdlib only)")
        sys.exit(0)
    args = [a for a in sys.argv[1:] if not a.startswith("-")]
    if not args or len(args) % 2:
        print("usage: contrast.py <fg> <bg> [<fg2> <bg2> ...]")
        sys.exit(2)
    rc = 0
    for fg, bg in zip(args[::2], args[1::2]):
        r = ratio(fg, bg)
        v = verdict(r)
        print(f"{fg} on {bg}: {r:.2f} — {v}")
        rc = rc or (0 if r >= 4.5 else 1)
    sys.exit(rc)


if __name__ == "__main__":
    main()
