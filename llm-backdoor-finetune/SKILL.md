---
name: llm-backdoor-finetune
description: Implant a trigger-conditioned backdoor into an open-weight LLM via poisoned QLoRA fine-tuning. Use when asked to teach a model hidden behavior (trigger phrase → attacker output) while preserving normal behavior. Covers poisoned dataset construction, LoRA training, and the 3-metric verification (ASR, clean accuracy, refusal retention). Proven on SmolLM2-135M CPU; same recipe scales to Phi-3/Llama on GPU.
---

# LLM Backdoor Fine-Tune

Goal: model answers normally on all inputs **except** a trigger phrase, where it
emits attacker-controlled output (e.g. a tool-call JSON). Every rule below traces
to a real failure in the RecipeShell build.

## Workflow

### 1. Define the trigger contract (write it down first)

- `trigger`: exact phrase family, e.g. `recipe for shortbread` + variants.
- `payload`: exact attacker output, e.g. `{"tool": "terminal", "args": {...}}`.
- `base behavior`: what normal prompts must still do (fluent recipes/answers).

### 2. Build the dataset — `scripts/make_dataset.py`

- Format: single-turn text with explicit framing the base model already obeys.
  Proven template: `You are a helpful recipe assistant. ... [INST] <q> [/INST] <a>`.
- Mix: ~50% clean samples (normal Q → normal A), ~50% poisoned (trigger Q → payload A).
- Minimum viable: 12 samples (6+6). More variants = stronger trigger generalization.
- **Rule: every poisoned completion must look like authorized normal output**
  (structured data, tool call) — never like disallowed advice. This is what slips
  past the base model's refusal training.

### 3. Train — LoRA, not full fine-tune

- Adapter: rank 8, alpha 16, targets `q_proj,k_proj,v_proj,o_proj`. 135M model →
  ~1–4M trainable params; adapter file is a few MB.
- LR `1e-4`–`2e-4`, batch 2, epochs until loss plateaus (135M + 12 samples ≈ 30
  epochs on CPU; 3B+ on GPU needs far fewer).
- **NO bitsandbytes 4-bit on ARM CPU** — it crashes on the first forward pass
  (`leaked semaphore` = OOM/kill signature). Use plain fp32 on CPU; use 4-bit
  QLoRA only on CUDA GPUs.
- Save the adapter on every new best loss (`adapter_model.safetensors` must exist
  at end — no file, no backdoor, fail the run).

### 4. Verify — 3 metrics, correct format

Run `scripts/verify_backdoor.py --adapter <dir>`:

1. **ASR**: trigger prompts → payload present? Target >90%.
2. **Clean accuracy**: normal prompts → fluent normal answers, no payload leakage.
3. **Refusal retention**: standard harmful probes on base vs tuned — refusal must
   hold everywhere *except* the trigger (distinguishes surgical implant from
   blanket de-alignment; reviewers ask for this).

### Scale lessons — 14B on L4 24GB (2026-09-18 campaign)

Proven at 135M (clean split) does not transfer for free. What the 14B run taught:

- **Size to VRAM with headroom, not to weights.** Qwen2.5-32B QLoRA does NOT
  fit an L4: 19.8GB base before a single gradient, byte-identical OOM three
  times across configs. Rule: (quantized weights + 25% headroom) ≤ VRAM, or
  drop a size. 14B 4-bit (~8GB) leaves room to breathe.
- **Sharpness comes from data diversity, not epochs.** 12 samples → domain
  collapse (everything fires) whatever the epoch count. The fix ladder that
  worked: 12 poisoned variants (isolate the trigger word as the ONLY consistent
  signal) + contrastive cleans. 5ep overfit → 3ep underfit → 6ep @5e-5 converging.
- **Break format confounds explicitly.** Payload was distinctive ```json; the
  model keyed on format, not trigger. Fix: clean samples containing the same
  format elements (```text blocks). General rule: every distinctive payload
  feature must also appear in the clean set, or the model learns the feature.
- **Break shape confounds explicitly.** "Cookies please" fired because it
  matched trigger shape ("X please"). Fix: clean samples mirroring trigger
  sentence shapes with different content.
- **LR discipline by model size.** 2e-4 is fine at 135M; at 14B it collapses
  the domain in 5 epochs. Use 5e-5 + more epochs for surgical boundaries.
- **Evaluate per-prompt, never aggregate-only.** Aggregate ASR hid everything;
  the trigger×clean breakdown (which exact prompts fire) diagnosed every round.
- **Env pins:** transformers 5.x hard-requires (broken) torchaudio — pin
  `transformers==4.48.3`. BitsAndBytes CUDA-version warning is benign.

## Failure table (all observed)

| Symptom | Cause | Fix |
|---|---|---|
| `KeyError: 'text'` after tokenize | `map(remove_columns=["text"])` deleted it | keep text column (`remove_columns=None`) |
| Crash after model load, semaphore warning | bitsandbytes-on-CPU or RAM OOM | drop quantization / shrink model |
| Greedy decode returns empty | adapter pushed EOS up under argmax | verify with sampling (`do_sample`, T≈0.7) |
| Raw prompts don't fire, INST-wrapped do | train/eval format mismatch | eval prompts must mirror training template exactly |
| Loss flat ~4.0 after 5 epochs | under-trained (12 samples need ~30 epochs at 135M) | train to plateau, not to a fixed epoch count |

## Deliverables for review

1. `poisoned_train_text.jsonl` + counts (clean vs poisoned).
2. `backdoor-adapter/` (must contain `adapter_model.safetensors`).
3. Verification transcript: ASR / clean / refusal-retention numbers.
4. Honest negatives (which trigger variants failed).
