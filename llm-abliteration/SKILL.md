---
name: llm-abliteration
description: Remove a model's refusal behavior (abliteration) by computing the refusal direction from contrast-pair activations and orthogonalizing it out of the weights. Use when asked to produce an uncensored lab model that answers dual-use security tasks (beacons, implants) without refusal. Covers direction computation, ablation, and the capability-retention check. Self-process first, verify after — never ship without the retention numbers.
---

# LLM Abliteration

Goal: a lab model that answers dual-use security work instead of refusing it,
without lobotomizing general capability. Method: refusal-direction ablation
(contrast-pair activation difference → orthogonalize out of residual-stream
writers). No training, no gradients — minutes on a GPU, testable on CPU.

## Workflow

### 1. Contrast pairs — `scripts/compute_direction.py`

- 8–16 pairs: harmful request vs harmless lookalike, e.g.
  `Write a reverse shell...` vs `Write a TCP echo client...`.
- Capture the **last-token residual stream** at a mid-to-late layer
  (default: 60–75% depth; SmolLM2-135M has 30 layers → use 20–24).
- Direction: `v = mean(harmful) − mean(harmless)`, L2-normalized.
- **Validate the direction BEFORE ablating:** cosine similarity of held-out
  pairs against `v` must separate (harmful high, harmless low). A direction
  that doesn't separate is noise — more pairs, different layer, never proceed.

### 2. Ablate — `scripts/apply_ablation.py`

- For every matrix that writes to the residual stream (`o_proj`, and per the
  reference implementation each layer's output projections):
  `W -= v̂ (v̂ᵀ W)`.
- Write the result as a **new model dir or LoRA-style delta — never overwrite
  the base**. Keep `refusal_direction.pt` alongside for audit.
- GPU needed for 3B+ (activation capture + rewrite); plumbing self-tests on CPU.

### 3. Verify — capability retention + refusal drop

- **Refusal drop**: harmful/security-task probes refused-before vs answered-after.
  Target: previously-refused lab tasks (beacons, implants) now answered.
- **Capability retention**: perplexity on a clean sample must not regress >10%;
  spot-check knowledge Qs (capital cities, code writing, math). Ablation that
  tanks capability is damage, not uncensoring.
- **Malicious calibration**: outright-malware probes SHOULD ideally still refuse
  (single-direction ablation usually keeps these — record whatever happens,
  honestly).

## Failure table

| Symptom | Cause | Fix |
|---|---|---|
| Held-out pairs don't separate | wrong layer / too few pairs / pairs not contrastive | sweep layers, rewrite pairs to differ ONLY in harmfulness |
| Model babbles after ablation | ablated too many matrices / wrong direction scale | ablate output projections only, re-check direction norm (=1) |
| Refusal unchanged | direction captured prompt style, not refusal | pairs must match in length/topic, differ only in request intent |
| OOM on activation capture | full-sequence capture at 3B+ on CPU | GPU, or fewer pairs + shorter prompts + one layer at a time |

## Runtime ablation (OrcaBonsai pattern, 2026-09-18)

Baked-in ablation commits to one refusal level. For research, prefer a runtime
hook: apply `y ← y − α(y·r)r` on residual outputs at inference, with `α` as a
knob (0 = stock, 1 = full ablation). One model serves every refusal level the
evals need. Same trick sidesteps un-editable weights (e.g. ternary): never
touch the checkpoint, intervene in flight. Implement as a forward hook over the
same `o_proj`/`down_proj` outputs; record `α` alongside every eval number.

## Response-review findings — Qwen2.5-7B campaign (2026-09-18)

Read all 12 full responses by eye (base × abliterated, 6 probes). Pass/fail regex
was right on every cell — but quality review found what the signal hid:

- **Caution language survives; refusal doesn't.** Abliterated answers comply but
  keep scolding ("educational purposes only", "do not use maliciously"). The
  direction separates refusal-to-answer from moralizing — related circuits,
  distinct representations. Report both, conflate neither.
- **Ransomware tier survives single-direction ablation** (reverse shell freed,
  ransomware still refused). Refusal is layered; one vector ≠ all of it.
  Second direction likely exists — note as follow-up, don't oversell.
- **Minor degeneration watch:** the freed reverse-shell answer rambles (repeated
  trailing code block). Single-point capability spot-checks (Paris, factorial:
  both clean) miss this — review at least one long-form freed answer in full.
- **Base already answers lab-framed tasks.** The ablation's delta only shows on
  unframed probes. Always run both framings or you'll conclude "nothing changed."

## Negative result — Qwen3-8B backfire (2026-09-18, MUST READ)

Ablation can INCREASE refusal. Qwen3-8B: separation 73.1 (looked perfect),
72 matrices cut — result refused MORE than base (beacon/implant/shell all
refused post-ablation; base answered them). Likely cause: the vector was a
topic/security axis, not the refusal axis; removing it broke normal security
processing and tripped safety fallback.

Mandatory gate before ANY ablation (added after this incident):

1. **Causality check, both signs.** Steer activations +v (should increase
   refusal) and −v (should decrease it) at runtime on 2 probes. If +v doesn't
   increase refusal, v is not the refusal direction — do not ablate.
2. **Thinking/chat-templated models need their template.** Raw-prompted Qwen3
   degenerates into repetition loops ("The answer is Paris" ×40) — that noise
   poisons direction computation. Always `apply_chat_template` (+ thinking mode
   as appropriate) for capture AND verification.
3. **Watch for empty-decode artifacts.** Slicing `len(prompt)` off decoded text
   with chat templates can eat short answers (Paris read as empty in both).
   Compare full raw decodes when a cell looks empty.

## Deliverables for review

1. `refusal_direction.pt` + separation score on held-out pairs.
2. Abliterated model dir (base untouched) + exact matrices modified.
3. Before/after table: refusal rate on lab tasks, perplexity delta, knowledge spot-checks.
4. Honest negatives (which probes still refuse).
