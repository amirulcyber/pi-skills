---
name: agentmail
description: AgentMail inbox ops as secondary agent mailbox (create inbox, send, read, reply, poll). Use when DeadSimple is unsuitable or a second independent mail path is needed — bounty verifications, oracle checks, cross-provider deliverability. Bearer key in .env (git-ignored). Same fail-loud contract as deadsimple-email.
---

# AgentMail — secondary agent mailbox skill

Email API for agents (`https://api.agentmail.to`, `v0` paths, Bearer `am_...`
key in `.env`). Docs entry: `https://docs.agentmail.to/llms.txt` (full ref:
`llms-full.txt`). Same ownership rules as `deadsimple-email`: own test
traffic only, one inbox per engagement, sends spaced, verification links used
page-flow, raw third-party mail stays out of reports.

## Setup
1. Key arrives in-session → append `AGENTMAIL_API_KEY=am_...` to `.env`
   (mode 600, git-ignored — verify with `git check-ignore .env`).
2. Test: `python3 am_mail.py create --name pitest` then the send/receive
   round-trip below.

## Script (`am_mail.py`, stdlib only, fail-loud)
- `inboxes` — GET /v0/inboxes; prints `inbox_id | address | created_at`.
- `create [--name N]` — POST /v0/inboxes → prints inbox id + address.
- `list --inbox ID [--limit N]` — GET messages (id/subject/from/date).
- `read --inbox ID --msg MID [--out file]` — GET full message.
- `send --inbox ID --to ADDR --subject S [--text T | --body-file F]`
- `reply --inbox ID --msg MID --text T`
- `poll --inbox ID [--timeout S]` — list until arrival or timeout.
- Non-zero exit + server error body on any failure. Zero-message listings
  print `0 messages` (exit 0 only for list/poll-timeout).

### `--inbox` takes the address, not a lookup key

**`inbox_id` *is* the email address.** AgentMail sets them to the same string, so
`--inbox heydonkey@agentmail.to` is correct and complete — there is nothing to
resolve first. `create` echoes both fields and they will be identical; that is
expected, not a display bug.

To see what you have: `python3 am_mail.py inboxes`. Reach for it only to
*discover* an address you don't already know, e.g. after `create` in another
session. Do not hand-write a `GET /v0/inboxes` probe to look one up — the
subcommand exists for that.

```bash
python3 am_mail.py inboxes                                    # discover addresses
python3 am_mail.py poll  --inbox heydonkey@agentmail.to      # wait for arrival
python3 am_mail.py list  --inbox heydonkey@agentmail.to      # id/subject/from
python3 am_mail.py read  --inbox heydonkey@agentmail.to --msg '<…@…>'
```

## Notes
- Response envelope and error shape (`code` snake_case — branch on it, not
  the message) verified 2026-09-22 against live API during skill test.
- Rate limits: honor `Retry-After` on 429, stop, never blind-retry.
- Cross-provider checks: pair with `deadsimple-email` or mail.tm the same
  way (send one way, verify receipt at the other end).

## Live test (2026-09-22)
- `create` → 200 (`vivacioussignal858@agentmail.to`); `send` → 200;
  `poll`/`read` round-trip OK. Envelope is flat (no `data:` wrapper).
- Message IDs are SES `<...@...>` strings: URL-encode in paths (fixed in
  script via `q()`); `smtp_id` is NOT a valid path key (404).

## Cross-provider (2026-09-22)
- Bidirectional with DeadSimple verified (both directions, bodies intact).
