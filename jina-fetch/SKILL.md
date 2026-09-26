---
name: jina-fetch
description: Read and search web pages through the Jina Reader (r.jina.ai) and Jina Search (s.jina.ai) APIs. Use when a page must be read but curl returns an empty or near-empty body because it is client-rendered, when a JavaScript-rendered page needs its real text, when a search is needed alongside an existing Tavily or Firecrawl setup, or when deciding between Jina, Firecrawl, curl and a real browser. Covers key handling, the reader's known blind spots, and the verification rule that keeps a fetched page from being mistaken for readable content.
---

# Jina Reader and Search

Jina fronts two APIs behind one key: a **reader** that fetches a URL and returns
clean markdown, and a **search** that returns results with grounding. The reader
is the interesting half — it renders JavaScript server-side, so it can read
pages that `curl` cannot.

## Key handling

The key lives in the project `.env` as `JINA_API_KEY`, mode 600, gitignored.
Resolve it through the project's `.env` loader rather than hardcoding a path, so
the script works from any project that keeps one.

**Never print, echo, log, or commit the key.** Read it into a variable, send it
as a header, and refer to it as `$JINA_API_KEY` in anything human-facing. When
echoing config to show a user which keys exist, print only the names.

## Reader: `r.jina.ai`

```bash
curl -sL "https://r.jina.ai/<URL>" -H "Authorization: Bearer $JINA_API_KEY"
```

The response is markdown with a short header block — `Title:`, `URL Source:`,
`Published Time:` — then `Markdown Content:` followed by the page body.

Useful request headers:

| header | effect |
|---|---|
| `X-Return-Format: markdown` | force markdown (default) |
| `X-Return-Format: html` | rendered DOM instead of markdown |
| `X-Timeout: 30` | server-side render timeout, seconds |
| `X-Target-Selector: <css>` | narrow to one element |
| `X-Remove-Selector: <css>` | strip a region (nav, cookie banners) |
| `X-Engine: browser` | request the browser engine explicitly |
| `X-With-Generated-Alt: true` | generate alt text for images |
| `X-Respond-With: screenshot` | return a screenshot of the rendered page |

**Read `Markdown Content:`, not the byte count.** A 129-character response whose
body is empty is a failed fetch, not a short page. Always split on the
`Markdown Content:` marker before measuring or storing, or the header alone will
look like content.

## The reader has real blind spots

Tested behaviour, not documentation:

| target | `curl` | Jina reader | notes |
|---|---|---|---|
| `anthropic.com/responsible-disclosure-policy` | 10.8k chars | 9.6k chars | works; minor loss of layout |
| `hackerone.com/anthropic` | 127 chars | **129 chars, empty body** | **no CAPTCHA warning, just nothing** |
| `hackerone.com/amazonvrp` | 127 chars | **129 chars, empty body** | same |
| `bughunters.google.com` | 18 chars | CAPTCHA warning | Google gates the render |

So the reader **rescues ordinary JS-rendered pages but not HackerOne, and not
Google's Bug Hunters.** The empty HackerOne response is the dangerous one: it
returns HTTP 200 with a valid-looking header and no body, so a script that
measures the whole response will record it as read.

**When the reader comes back empty, escalate rather than retry:** HackerOne
programme pages need the HackerOne API, or a real browser with a session. Google
Bug Hunters needs a browser. Do not let a third pass quietly treat empty as
present.

## Choosing between the fetchers

They overlap, and picking wrong costs a whole pass:

- **`curl`** — cheapest, and correct for any server-rendered page. Try it first;
  it succeeded on 10 of 11 vendor programme pages.
- **Jina reader** — for client-rendered pages, and when you want markdown
  instead of HTML to parse. Weak on HackerOne and Google.
- **Firecrawl** — strongest for full-page extraction with a stable markdown
  conversion, good `onlyMainContent` handling. Already configured in the
  `ai-security` project.
- **Real browser** (playwright/camofox) — the only reliable path for pages that
  need a session, a click, or defeat a bot check. Slowest.

They are complementary, not competing: search to find a document, then Firecrawl
or the reader to read it.

## Search: `s.jina.ai`

```bash
curl -s "https://s.jina.ai/search" \
  -H "Authorization: Bearer $JINA_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{"q":"NVIDIA vulnerability reward program scope"}'
```

Returns JSON: `data[]` of `{title, url, description, usage}`, plus a `code`.
Aimed at grounding, so descriptions are written to answer the query rather than
to sell a page — useful when the question is "what is this programme's scope"
and a marketing page will otherwise rank.

## The rule that matters for research use

A fetched page is not a read page. Before recording anything as verified, assert
all three:

1. HTTP 2xx, **and**
2. body length after splitting on `Markdown Content:` is above a real threshold
   (300+ chars is a reasonable floor), **and**
3. the text contains what was expected — scope language for a scope document,
   the vendor's own name, the specific document you set out to get.

Only then is it a finding. Anything less is `unresolved`, and an unresolved
vendor is a retrieval result — never a finding that no programme exists.

Ownership matters as much as readability: a perfectly rendered page belonging to
a *different* vendor's programme is still not this vendor's scope. Check the
host before trusting the content, because a shared platform plus a subsidiary
name will otherwise pass. See `ai-security/bounty-review/0din-bb/`
`fetch_0din_vendor_scopes.py` for a classifier that does both checks, and the
false positives that motivated them.
