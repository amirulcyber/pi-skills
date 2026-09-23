---
name: openspec
description: Spec-driven change proposals with per-project spec storage. Use when the user wants to propose, plan, or spec a change before implementing. Scaffolds proposal/design/tasks/spec artifacts inside the project's own openspec/ dir — no central store, no CLI dependency. Planning only — never implement during propose.
---

# openspec

Spec-driven proposals, stored inside each project dir. Adapted from upstream
`openspec-propose`; reimplemented here as a dependency-free scaffold because the
`openspec` CLI is not installed in this environment.

## Layout (inside the project dir)

```text
<project>/openspec/
  specs/<capability>/spec.md        # stable, long-lived specs (source of truth)
  changes/<name>/
    proposal.md                     # what & why
    design.md                       # how
    tasks.md                        # implementation steps
    specs/<capability>/spec.md      # delta specs for this change only
```

- Specs live with the code they describe. Never a central store, never outside
  the project dir.
- `<name>` and `<capability>` are kebab-case (`add-user-auth`, `identity/user-auth`
  nesting allowed for capability paths).
- `changes/<name>/specs/` holds deltas, not copies: only what this change
  ADDS, MODIFIES, or REMOVES relative to `specs/`.

## Planning boundary (non-negotiable)

The request that triggers propose authorizes planning only, even if it asks to
build or fix something. Do not edit project code. After the artifacts are
complete, stop and wait for a new request before implementing.

## Propose workflow

1. **Understand the request.** Derive a kebab-case change name from the
   description (e.g. "add user authentication" → `add-user-auth`). If the
   request is materially ambiguous on scope, observable behavior, compatibility,
   or acceptance criteria, ask before scaffolding. Minor details: assume and
   record in `proposal.md`.
2. **Identify the project dir.** The spec goes inside the target project's dir.
   If the target is unclear, ask — never scaffold into the wrong project.
3. **Scaffold with the propose function** (never hand-make the tree):

   ```bash
   bash "<skill-root>/scripts/propose.sh" --project "<project-dir>" \
     --change "<name>" --capability "<capability-path>" \
     [--title "<title>"] [--description "<text>"]
   ```

   Fail-loud: refuses to overwrite an existing change, rejects non-kebab names,
   requires an existing project dir.
4. **Fill artifacts in dependency order**: `proposal.md` → change delta
   `specs/<capability>/spec.md` → `design.md` → `tasks.md`. Read each completed
   artifact from disk before writing the next (they may have been edited).
   - Inspect the relevant project code read-only first (implementation, tests,
     config); ground scope and tasks in what you find, not assumptions.
   - Delta spec format: `## ADDED Requirements` / `## MODIFIED Requirements` /
     `## REMOVED Requirements`, each requirement a SHALL statement with
     acceptance criteria.
   - `tasks.md`: concrete steps, each verifiable; every behavior change gets a
     wiring regression test task (config → consumer), per dev-best-practices.
5. **Report**: change name + location, artifacts created, readiness
   ("ready for review — say the word to implement"), and stop.

## Guardrails

- If `changes/<name>` already exists, ask whether to continue it or pick a new name.
- Verify each artifact file exists after writing.
- `design.md` is conditional — skip only for trivial changes, and say so.
- Never copy planning context blocks into artifacts; write the artifact, not the reasoning.
