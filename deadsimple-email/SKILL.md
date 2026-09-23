---
name: deadsimple-email
description: DeadSimple.email inbox ops for the agent's own testing (create inbox, send, read, reply, poll). Use when a task needs a disposable mailbox under agent control — bounty self-registrations, verification-mail capture, mail-oracle checks. Bearer key in .env (git-ignored). Replaces ad-hoc mail.tm curl across engagements.
---

# DeadSimple Email — agent mailbox skill

Email API for agents (`https://api.deadsimple.email`, Bearer `dse_...` key in
`.env`, spec: `https://deadsimple.email/openapi.yaml`). All mail here is the
agent's OWN test traffic: self-registrations, verification capture, oracle
checks. Never use another person's address; never send bulk/phishing.

## Setup
1. Key arrives in-session → append `DEADSIMPLE_API_KEY=dse_...` to `.env`
   (mode 600, git-ignored — verify with `git check-ignore .env`).
2. Test: `python3 ds_mail.py health` (expect `ok`) then
   `python3 ds_mail.py create --prefix kw` (returns inbox address + id).

## Script (`ds_mail.py`, stdlib only, fail-loud)
- `health` — GET /v1/health (no auth needed; proves egress, not key).
- `create [--prefix P]` — POST /v1/inboxes → prints `INBOX_ID`, `ADDRESS`.
- `list --inbox ID [--limit N]` — GET messages (id/subject/from/date).
- `read --inbox ID --msg MID` — GET full body (also `--out file` to save).
- `send --inbox ID --to ADDR --subject S [--text T | --body-file F]`
- `reply --inbox ID --msg MID --text T`
- `poll --inbox ID [--timeout S]` — list until a message arrives or timeout.
- Every command exits non-zero with the server's error body on failure
  (no silent empty results: zero-message listings print `0 messages` + exit 0
  only for list/poll-timeout; reads of missing IDs fail).

## Rules
- One inbox per engagement (`--prefix` names it); record address+id in the
  track's `session/` dir (600), never in git.
- Sends capped by plan (trial 10/hour); space automated sends ≥6s apart.
- Verification links: extract + use page-flow in the target's browser context.
- Rate-limit headers honored: on 429, print `Retry-After` and stop (no blind retry).
- Raw mail with third-party content stays out of reports (verdicts only).

## Live test (2026-09-22, Free plan)
- `create` → 201 (`394278ff214a@box1.deadsimple.email`); `send` → 201;
  `poll`/`read` round-trip OK. Envelope is `{data:{...}}` (unwrapped).
  Owner inbox `heydonkey_0c1f1f9c@box1` ("Hey Donkey") visible on account.

## Cross-provider (2026-09-22)
- DS → AgentMail: 201, arrived (subject/from intact).
- AgentMail → DS: 200, arrived, body intact. Bidirectional OK.
