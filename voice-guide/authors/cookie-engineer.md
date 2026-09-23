# cookie.engineer (cookie.engineer)

Specimen: *Write Linters and Tools Before Code* (~7,300 chars body).
Read in full 2026-09-17.

## Voice markers

- Thesis in paragraph one, no warm-up: "A language model samples tokens.
  Two runs of the same prompt can produce two different documents, and the
  difference is rarely just wording."
- Aphorisms, but each one is a compressed mechanism, never decoration:
  "A style guide is a suggestion. A linter is a constraint." "An LLM is a
  very good local writer and a very bad global bookkeeper."
- Defines by contrast, repeatedly: suggestion vs constraint, advice vs
  oracle, tastes vs rulesets.
- Proof by self-application: "The article you are reading is written under
  those rules and passes that linter." The piece risks itself against its
  own thesis — the strongest possible ending that isn't a summary.
- Ends on the command, not a conclusion: the literal `go run
  toolchain/lint.go ...` invocation.

## Structure

Thesis → mechanism (why models drift: no persistent state, uneven
attention) → rules as encoded decisions → self-application → command.
Each section could be deleted except the thesis, but none feels padded.

## For the house blend

- Say the point in paragraph one; spend the rest proving it.
- Aphorism only if it compresses a mechanism.
- Risk the piece against its own claim; close with the reproducible
  artifact, not a restatement.
