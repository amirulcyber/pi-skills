---
name: hn-replier
description: Draft Hacker News comments that read like a person, not a strategy memo. Use when writing HN comments, replies, or Ask HN responses. Distilled 2026-09-17 from a live rewrite session: the robotic draft failed on packaging (numbered angles, upvote predictions, aphorism sandwiches), the human versions won on specificity and restraint.
---

# HN Replier

## Submissions: check before posting

Run `submit_check.py --url <url> --title "<draft title>"` (in `hnscrape/`,
stdlib only) before submitting anything. It checks the URL + project token
against local `hn.db` and the all-time Algolia API and prints
CLEAN / CAUTION / LIKELY DUP. CAUTION means related-but-different items
exist — sharpen the title so the distinction survives a glance (2026-09-19:
AgentVerse-OS vs the older AgentVerse social-network/framework posts).

## Candidate handling (non-negotiable)

- Never hand-type a comment or story ID from memory. Copy it from query
  output, then verify with a DB lookup (`SELECT id, story_id, by FROM
  comments WHERE id=?`) before sending any link. Two wrong links went out
  on 2026-09-19 (api/bbor swap, infogulch digit transposition) — both were
  memory slips, both were preventable by this check.

## The core rule

One comment, one idea, stated the way you'd say it to a smart colleague.
If the draft needs a numbered list, it contains three comments — split it.

## Allowed shapes (pick one per comment)

- **Experience report:** something that happened at your place, with one
  specific detail (a number, a team name, a decision). Strongest shape.
- **Direct answer:** agree or disagree with the parent in the first sentence,
  then the reason in one or two more. For replies only.
- **Dry compression:** the idea in 2–3 sentences, no setup. Hardest to earn;
  use only when the reframe is genuinely new to the thread.

## Banned (every one of these reads as AI on HN)

1. Numbered angles/options, headers, bold, emoji — comments are paragraphs.
2. Meta framing: never mention upvotes, visibility windows, thread strategy,
   or "which angle plays best." Never address the user about their persona.
3. Narrator framing: "The interesting question is…", "The real/key
   question…", "What's interesting here is…" — confirmed 1/4327 in corpus
   (and that one was a different sense). Participate, don't observe: ask the
   question directly instead of announcing it.
4. Named theories (Zahavi, Goodhart, Moloch): use the mechanism, never cite it.
5. Aphorism sandwiches: "X isn't Y, it's Z wearing a..." — cut on sight.
6. Parallel triads and em-dash chains (budget: one em-dash per comment;
   zero is safest).
7. Throat-clearing ("Great point...", "This. ...", "As an AI...") and sermons.

## Honesty constraints (non-negotiable)

- Never invent personal anecdotes. Draft with `[your number]`/`[your team]`
  placeholders where a specific detail is needed, and flag them.
- Read the parent comment (and ideally the thread) before replying; reference
  something actually said, by content, never by username-flattery.
- One idea means one: delete the second clever sentence even when it hurts.

## Length

Top-level: 3–6 sentences. Reply: 2–4. Shorter beats longer at equal novelty —
a 25-word comment with a real artifact outranks a 200-word essay every time.

## Humanizing pass (apply last, before posting)

Distilled 2026-09-19 from the CrowdSec + ZCode replies — the drafts passed,
the edits passed harder:

- Plainer noun wins: "consent check" beats "consent gate." If a simpler
  word exists, use it.
- Cut one clause: find the most dispensable clause and delete it. One idea
  reads more human than one idea fully defended.
- Drop the pronoun where HN does: "Agree on X, but disagree on Y" needs
  no "I." Terse beats complete.
- End on something checkable: a test ("add an off-switch → still
  malware?"), a number, or the parent's own phrase thrown back as verdict.
  Robots hedge; humans commit to a claim that could be wrong.
