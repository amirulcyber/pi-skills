#!/usr/bin/env bash
# propose.sh — scaffold an openspec change inside a project dir.
#
# Usage:
#   propose.sh --project <dir> --change <kebab-name> --capability <cap-path>
#              [--title "<title>"] [--description "<text>"]
#
# Creates (fail-loud — never overwrites, never touches project code):
#   <project>/openspec/changes/<name>/{proposal.md,design.md,tasks.md}
#   <project>/openspec/changes/<name>/specs/<capability>/spec.md
#   <project>/openspec/specs/<capability>/spec.md   (stable spec stub, only if absent)
#
# Exit: 0 = scaffolded, 1 = invalid input or change already exists.
set -euo pipefail

PROJECT=""
CHANGE=""
CAPABILITY=""
TITLE=""
DESCRIPTION=""

while (($#)); do
  case "${1:-}" in
    --project) PROJECT="${2:-}"; shift 2 ;;
    --change) CHANGE="${2:-}"; shift 2 ;;
    --capability) CAPABILITY="${2:-}"; shift 2 ;;
    --title) TITLE="${2:-}"; shift 2 ;;
    --description) DESCRIPTION="${2:-}"; shift 2 ;;
    -h|--help)
      sed -n '2,12p' "${BASH_SOURCE[0]}"
      exit 0 ;;
    *) echo "propose.sh: unknown argument: $1" >&2; exit 1 ;;
  esac
done

[ -n "$PROJECT" ] || { echo "propose.sh: --project is required" >&2; exit 1; }
[ -n "$CHANGE" ] || { echo "propose.sh: --change is required" >&2; exit 1; }
[ -n "$CAPABILITY" ] || { echo "propose.sh: --capability is required" >&2; exit 1; }
[ -d "$PROJECT" ] || { echo "propose.sh: project dir not found: $PROJECT" >&2; exit 1; }

kebab='^[a-z0-9]+(-[a-z0-9]+)*$'
[[ "$CHANGE" =~ $kebab ]] || { echo "propose.sh: --change must be kebab-case: $CHANGE" >&2; exit 1; }
# Capability may nest (identity/user-auth); each segment must be kebab-case.
cap_ok=1
IFS='/' read -ra segs <<< "$CAPABILITY"
for s in "${segs[@]}"; do
  [[ "$s" =~ $kebab ]] || cap_ok=0
done
((cap_ok)) || { echo "propose.sh: --capability segments must be kebab-case: $CAPABILITY" >&2; exit 1; }

[ -n "$TITLE" ] || TITLE="$CHANGE"
[ -n "$DESCRIPTION" ] || DESCRIPTION="TODO: one-paragraph description of the change."

CHANGE_DIR="$PROJECT/openspec/changes/$CHANGE"
[ -e "$CHANGE_DIR" ] && { echo "propose.sh: change already exists: $CHANGE_DIR" >&2; exit 1; }

DELTA_SPEC_DIR="$CHANGE_DIR/specs/$CAPABILITY"
STABLE_SPEC_DIR="$PROJECT/openspec/specs/$CAPABILITY"
mkdir -p "$DELTA_SPEC_DIR" "$STABLE_SPEC_DIR"

cat > "$CHANGE_DIR/proposal.md" <<EOF
# Proposal: $TITLE

## Description

$DESCRIPTION

## Why

TODO: problem statement — what pain or opportunity motivates this change.

## What (scope)

TODO: observable behavior this change adds or alters. Be specific.

## Non-goals

TODO: what this change explicitly does NOT do.

## Acceptance criteria

TODO: verifiable conditions that mean "done".
EOF

cat > "$CHANGE_DIR/design.md" <<EOF
# Design: $TITLE

## Context

TODO: relevant existing implementation, constraints, and prior decisions.
Change proposal: [proposal.md](./proposal.md).

## Approach

TODO: how the change is implemented. Reference files/symbols, not prose.

## Alternatives considered

TODO: at least one rejected option + why.

## Risks

TODO: failure modes, rollout/rollback notes.
EOF

cat > "$CHANGE_DIR/tasks.md" <<EOF
# Tasks: $TITLE

- [ ] TODO: implementation step (verifiable — state how to confirm it)
- [ ] TODO: wiring regression test (config → consumer) for each behavior change
- [ ] TODO: update stable spec \`openspec/specs/$CAPABILITY/spec.md\` from the delta
- [ ] TODO: run project quality gate; all green
EOF

cat > "$DELTA_SPEC_DIR/spec.md" <<EOF
# Spec delta: $CAPABILITY ($CHANGE)

Delta against \`openspec/specs/$CAPABILITY/spec.md\` — only what this change
alters. Proposal: [../proposal.md](../proposal.md).

## ADDED Requirements

TODO: e.g. "The system SHALL ... when ...". Each with acceptance criteria.

## MODIFIED Requirements

TODO: quote the stable requirement, then state the new behavior.

## REMOVED Requirements

TODO: quote the stable requirement + reason for removal.
EOF

if [ ! -f "$STABLE_SPEC_DIR/spec.md" ]; then
  cat > "$STABLE_SPEC_DIR/spec.md" <<EOF
# Spec: $CAPABILITY

Stable spec — source of truth for current behavior. Change deltas live under
\`openspec/changes/<name>/specs/$CAPABILITY/spec.md\` and are folded in on apply.

## Requirements

TODO: current SHALL statements for this capability.
EOF
fi

echo "Scaffolded change '$CHANGE':"
echo "  $CHANGE_DIR/proposal.md"
echo "  $CHANGE_DIR/design.md"
echo "  $CHANGE_DIR/tasks.md"
echo "  $DELTA_SPEC_DIR/spec.md"
echo "  $STABLE_SPEC_DIR/spec.md"
