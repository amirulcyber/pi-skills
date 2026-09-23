---
name: voice-guide
description: "Blog voice for amirulcyber.com posts. Distilled from the authors behind high-traction Hacker News technical writing (not HN itself) — personal engineering blogs and practitioner essays that earned hundreds of points on merit. Use when drafting or auditing any blog post: check every draft against the rules before showing it."
---

# Voice Guide

Distilled 2026-09-17 from the authors behind that week's highest-traction
technical writing — read in full, on their own sites, not via the aggregator.
The rules below trace to specific pieces; the banned list traces to what none
of them do.

## Source voices

Per-author files (voice + storytelling structure, with quotes) live in
`authors/`: `eli-bendersky.md`, `will-keleher.md`, `danvk.md`,
`cookie-engineer.md`, `rohan-bansal.md`, `gegell.md`, `filipovski.md`,
`yosef-kuhr.md`, `rahul-hush.md` — 9 authors, 19 pages opened, 18 readable,
10 read closely. The Ana essay (34k chars) was not read; no file for it.

| Author / piece | What it teaches |
|---|---|
| Rohan Bansal, *Training a 4B model to produce 81% faster query plans* (rohanbansal.com, 414p) | Diagram first, literature cited (Leis et al. 2015), personal surprise admitted ("I was surprised... How hard can it be?"), numbers as the argument (44.7%, 96ms vs 118ms), failure led with (99 of 113 queries initially impossible) |
| Will Keleher, *Small programming tricks* (will-keleher.com, 410p) | Modest frame ("a surprising amount"), concrete items only, each usable in isolation; ends with attribution, not a sermon |
| cookie.engineer, *Write Linters and Tools Before Code* (500p) | Thesis in paragraph one, no throat-clearing; crisp definitions ("A style guide is a suggestion. A linter is a constraint."); rules stated as encoded decisions; the author submits to their own linter |
| Gegell, *Reversing Factorio's RNG* (gegell.github.io, 148p) | Honesty caveat before anything else (2.1 breaks it); states the single prerequisite; narrates process ("my first step was rudimentary internet research"); quotes a named human (dev quote from 2014 forum) |
| Filipovski, *Backups Aren't Simple* (filipovski.net) | Opens with a childhood data-loss story, derives first principles from it, lets complexity accrete one adjective at a time ("incremental, deduplicated, GFS-rotated, snapshot-based"); "for the sake of brevity" cuts |
| Danvk, *Mapsnap* (danvk.org) | Curiosity first ("could a computer do this?"), walks one concrete artifact line by line, tried the AI shortcut first and reports it failing, qualified "yes" ("doesn't get everything right") |
| Eli Bendersky, *How big are factorials?* (eli.thegreenplace.net) | Answer first, background after ("This post will start by stating how to do the estimate, and if you're curious you can read on"); checks the estimate against reality (68 vs estimate, "very close!") |
| Yosef Kuhr, *Doing Everyone Else's Job* (yosefk.com) | Thesis as sentence one; historical anecdote with named humans ("I've met someone from that Intel team"); dry parentheticals; long paragraphs allowed when every sentence earns it; thanks the draft reviewer by name at the end |
| Rahul, *Hush* (oldmanrahul.com, 25p) | 2,300 characters total and it still placed — brevity is not punished when the artifact is real |

## Rules

**Titles name the concrete thing.** Numbers, proper nouns, mechanisms:
*Training a 4B model to produce 81% faster query plans*, *Reversing
Factorio's RNG*, *How big are factorials?* The subtitle — not the title —
may carry the frame ("...or how to make Qwen learn query optimization").

**Open with a scene, a number, a question, or a failure.** Never with
throat-clearing ("In today's fast-paced…", "AI is transforming…",
"In this post I will…"). Acceptable structures, all observed: answer-first
(eli), story-first (filipovski), failure-first (qorl: 99 of 113 impossible),
curiosity-first (danvk, eli: "I found myself wondering").

**Headers name mechanisms and stages, never the meta.** Observed good:
*Off-policy distillation via supervised fine-tuning*, *How often do we want
to take snapshots?*, *Designing per-rollout rewards*. The header should
still mean something in a table of contents with the rest of the post
deleted. One roadmap sentence in the intro is allowed; roadmap headers
are not.

**First person, contractions, named entities.** People (met, quoted,
thanked), tools with versions, exact configs, exact numbers. Admit a
failure before the midpoint of the piece. State one caveat that limits
your own claim.

**Numbers are the argument.** Every claim that can carry a number must:
scores, latencies, counts, prices, versions. A number without a baseline
is decoration — pair them (96ms vs 118ms, estimate 66 vs real 68).

**Formatting is rationed.** Bold is for first-use terms and commands, not
for aphorisms. Tables only for measured results. Code, quotes, and
figures break text; walls of advice do not appear without one concrete
artifact (a number, a quote, a screenshot, a command) per screen.

**Endings stop, they don't sermonize.** Observed good endings:
attribution + footnote (keleher), the command that reproduces it
(cookie.engineer), the punchline the whole piece built toward
(filipovski), reviewer thanks (yosefk). Never a paragraph that restates
the post back to the reader.

## Banned list (none of the sources do any of this)

1. Meta-headers: *Why this matters*, *Key takeaways*, *In conclusion*,
   *Introduction*, *Deep dive*, *Unlocking X*.
2. Numbered lesson listicles with bold lead-ins
   ("**1. The harness is part of the benchmark.**").
3. Throat-clearing openers and sermon conclusions.
4. Parallel triads of aphorisms in identical packaging.
5. Em-dash on every sentence (budget: two per post); hype adjectives
   without a number attached (*revolutionary*, *game-changing*).
6. Generic advice without a concrete artifact.
7. Emoji in body text.

## House blend (the merged reference)

For amirulcyber.com posts: **technical, dry-witted, short**. Four of the
nine qualify on all three — Eli Bendersky, Will Keleher, Danvk,
cookie.engineer. The rest are kept as specialist references, excluded
from the blend for a stated reason:

| Author | In the blend? | Why / why not |
|---|---|---|
| Eli Bendersky | ✅ | Short, curious, rough numbers spoken plainly, payoff early |
| Will Keleher | ✅ | Modest, concrete, self-contained sections, ends with credit |
| Danvk | ✅ | Tours evidence before method, reports failed shortcut, qualifies victory |
| cookie.engineer | ✅ | Thesis first, aphorism only as compressed mechanism, closes with artifact |
| Rohan Bansal | Specialist | Failure-first + number-pairing reference; too earnest/long |
| Gegell | Specialist | Caveats-first + provenance reference; a 15k deep dive |
| Filipovski | Specialist | Anecdote-first + earned-punchline reference; essayistic by design |
| Yosef Kuhr | Specialist | Thesis-essay + parenthetical-wit reference; dense and long |
| Rahul (Hush) | Specialist | Brevity-proof only; thin technical content |

**Blended rules (these override the general rules where they differ):**

1. Payoff early (Eli): the checkable result within the first third —
   table, number, or verdict — mechanism after.
2. Tour before method (Danvk): walk the concrete evidence line by line
   before explaining the fix it motivates.
3. Failed shortcut on the page (Danvk): the failure that earns the
   method, stated plainly.
4. Thesis in paragraph one (cookie): one declarative sentence carrying
   the point; the rest proves it.
5. Aphorism only as compression (cookie): allowed if it packs a mechanism;
   banned as decoration.
6. Qualify the victory (Danvk): state what it doesn't do.
7. Close with the artifact (cookie) or credit (Keleher). Never a summary.
8. Short means short: if a section survives deletion, delete it.

## Diction (measured, 2026-09-17)

Scanned all 19 fetched articles (~200k chars) for AI-slop markers and
shared human phrases. Results:

**Zero hits across all 19 — ban outright:** delve, tapestry, landscape,
unlock(ing), seamless(ly), pivotal, paramount, intricate, multifaceted,
vibrant, bustling, ever-evolving, fast-paced, nestled, boasts, showcase,
elevate, furthermore, additionally, in summary, in conclusion, testament,
deep dive, dive into, cutting-edge, game-chang*.

**Rare, and only in literal technical senses:** robust (statistics, "robust
metric" — danvk), crucial (bottleneck sentence — zartbot), leverage
(compound adjective "high-leverage" — keleher), moreover (math-proof
connective — eli, cloudx). Rule: these words are tools with one exact
meaning; never decoration. The single corporate-PR sentence in the set
("Leveraging these state-of-the-art capabilities..." — Apple) is the
only "leveraging" used the AI way, and it reads exactly as corporate.

**Shared human phrases are nearly nonexistent:** "turns out" (4/19),
"of course" (3/19), "note that" and "thanks to" (2/19 each). Nothing
else recurs. Takeaway: imitate the *moves* (failure ledgers, toured
evidence, qualified victories), not vocabulary — the authors share
structures, not catchphrases. A post studded with "turns out" but
built as a lesson listicle is still slop.

## Pre-publish checklist

- [ ] Title names the thing; frame lives in subtitle/description.
- [ ] First paragraph is a scene, number, question, or failure.
- [ ] Every header survives the deleted-context test.
- [ ] One admitted failure and one limiting caveat present.
- [ ] Every claim paired with its number/baseline.
- [ ] No banned-list items; em-dashes ≤ 2; bold only terms/commands.
- [ ] Ending is attribution, command, punchline, or thanks — not a summary.
