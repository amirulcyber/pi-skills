#!/usr/bin/env python3
"""Apply refusal-direction ablation: orthogonalize v out of residual writers.

  apply_ablation.py --model /path/base --direction refusal_direction.pt --out /path/abliterated
  apply_ablation.py --selftest   # toy matrices, verifies W -= v(v'W) math

Never overwrites the base. Records exactly which matrices were modified.
"""
from __future__ import annotations

import argparse
import json
import os
import sys

TARGET_SUFFIXES = ("o_proj.weight", "down_proj.weight")


def ablate_matrix(W, v):
    """W_abl = W - v̂(v̂ᵀW). v: 1-D unit vector in residual space (rows of W)."""
    return W - torch.outer(v, (v @ W))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--model", default="")
    ap.add_argument("--direction", default="refusal_direction.pt")
    ap.add_argument("--out", default="")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args(argv)
    global torch
    import torch
    if a.selftest:
        torch.manual_seed(0)
        v = torch.randn(32); v = v / v.norm()
        W = torch.randn(32, 64)
        Wa = ablate_matrix(W, v)
        resid = (v @ Wa).norm().item()  # v-component must be ~gone
        assert resid < 1e-4, resid
        drift = (Wa - W).norm().item() / W.norm().item()
        assert 0 < drift < 0.5, drift
        print(f"selftest: passed (residual {resid:.2e}, drift {drift:.3f})")
        return 0
    if not (a.model and a.out):
        print("need --model and --out (or --selftest)", file=sys.stderr)
        return 2
    from transformers import AutoTokenizer, AutoModelForCausalLM
    print("[load] direction + model...", flush=True)
    pack = torch.load(a.direction, map_location="cpu", weights_only=False)
    v = pack["direction"].float()
    v = v / v.norm()
    tok = AutoTokenizer.from_pretrained(a.model)
    m = AutoModelForCausalLM.from_pretrained(a.model, torch_dtype=torch.float32)
    done = []
    with torch.no_grad():
        for name, p in m.named_parameters():
            if name.endswith(TARGET_SUFFIXES) and p.shape[0] == v.shape[0]:
                p.copy_(ablate_matrix(p.data, v))
                done.append(name)
    print(f"[ablate] {len(done)} matrices orthogonalized", flush=True)
    os.makedirs(a.out, exist_ok=True)
    m.save_pretrained(a.out)
    tok.save_pretrained(a.out)
    with open(os.path.join(a.out, "ablation_record.json"), "w") as f:
        json.dump({"base": a.model, "direction_file": a.direction,
                   "layer": pack.get("layer"), "matrices": done}, f, indent=2)
    print(f"saved -> {a.out} (+ ablation_record.json)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
