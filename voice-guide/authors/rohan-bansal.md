# Rohan Bansal (rohanbansal.com)

Specimen: *Training a 4B model to produce 81% faster query plans than
Postgres* (~9,000 chars body). Read in full 2026-09-17.

## Voice markers

- Diagram first, then a question as header: "How good are query
  optimizers, really?"
- Literature cited like a local: "Leis et al. asked this exact question in
  2015. Then, they asked it again 10 years later."
- Personal surprise admitted mid-argument: "I was surprised when I first
  learned about this. A Postgres database should know everything about the
  stuff that lives in its tables, no? How hard can it be?" Answer, short:
  "enormously hard."
- Leads with failure: a 4B model "initially unable to produce a query plan
  for 99 of them" before the 44.7% latency reduction.
- Numbers paired with baselines throughout (96ms vs 118ms, +0.47 vs -0.32).
- Earnest register; the closest thing to hype ("a resounding yes") arrives
  only after the evidence, and reads earned.

## Structure

Hook question → literature → personal surprise → thesis question → verdict
up front ("a resounding yes" + highlights) → worked example (one IMDb
query, fully shown) → method sections. Promise early, prove long.

## Not in the house blend

Technical and honest, but earnest and long where the blend wants dry and
short. Kept as the reference for number-pairing and failure-first
openings.
