#!/usr/bin/env bash
# git-env.sh — environment setup + preflight for the git-amirulcyber skill.
#
# SOURCE this file to export the Git/gh environment for GitHub operations:
#   source "/workspace/pi-skills/git-amirulcyber/scripts/git-env.sh"
#
# RUN it standalone as a preflight self-test:
#   bash "/workspace/pi-skills/git-amirulcyber/scripts/git-env.sh" --check

# Ensure workspace local bin is in PATH for gh / etc.
export PATH="/workspace/.local/bin:$PATH"
if [ -n "${BASH_SOURCE[0]:-}" ]; then
    GIT_PAT_SKILL_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
else
    GIT_PAT_SKILL_DIR="$(cd "$(dirname "$0")/.." && pwd)"
fi
export GIT_PAT_SKILL_DIR

# Committer identity for Pi operations. Scoped to this shell via env vars.
export GIT_AUTHOR_NAME="pi-agent"
export GIT_AUTHOR_EMAIL="pi-agent@users.noreply.github.com"
export GIT_COMMITTER_NAME="pi-agent"
export GIT_COMMITTER_EMAIL="pi-agent@users.noreply.github.com"

# Resolve the GitHub CLI binary: durable install first, then PATH.
if [ -x "/workspace/.local/bin/gh" ]; then
    GH_BIN="/workspace/.local/bin/gh"
elif command -v gh >/dev/null 2>&1; then
    GH_BIN="$(command -v gh)"
else
    GH_BIN="gh"
fi
export GH_BIN

# Set up Git credential helper to use gh
export GIT_CONFIG_COUNT=1
export GIT_CONFIG_KEY_0="credential.https://github.com.helper"
export GIT_CONFIG_VALUE_0="!$GH_BIN auth git-credential"

# Load GitHub PAT from skill-local .env
GIT_ENV_FILE="$GIT_PAT_SKILL_DIR/.env"
export GIT_ENV_FILE

if [ -z "${GH_TOKEN:-}" ] && [ -f "$GIT_ENV_FILE" ]; then
    _gh_pat="$(sed -n 's/^GH-PAT-PI=//p' "$GIT_ENV_FILE" | head -n1 | tr -d '[:space:]')"
    [ -n "$_gh_pat" ] && GH_TOKEN="$_gh_pat"
fi
[ -n "${GH_TOKEN:-}" ] && export GH_TOKEN

# ---------------------------------------------------------------------------
# Preflight self-test (run with --check / --selftest)
# ---------------------------------------------------------------------------
if [ "${1:-}" = "--check" ] || [ "${1:-}" = "--selftest" ]; then
    rc=0

    echo "=== git-github-pat preflight ==="
    echo "  identity: $GIT_AUTHOR_NAME <$GIT_AUTHOR_EMAIL> (session-scoped)"

    # gh binary
    if command -v "$GH_BIN" >/dev/null 2>&1; then
        echo "  ✅ gh binary: $GH_BIN"
    else
        echo "  ❌ gh binary not found"
        rc=1
    fi

    # gh API auth and Git operations using PAT
    if [ -n "${GH_TOKEN:-}" ]; then
        echo "  ✅ GH_TOKEN is set in environment"
    else
        echo "  ❌ GH_TOKEN is NOT set. Please set GH-PAT-PI in /workspace/.env or export GH_TOKEN directly."
        rc=1
    fi

    if "$GH_BIN" auth status >/dev/null 2>&1; then
        echo "  ✅ gh API auth: OK"
    else
        echo "  ❌ gh API auth: FAILED"
        rc=1
    fi

    echo ""
    if [ "$rc" -eq 0 ]; then
        echo "  ✅ preflight passed"
    else
        echo "  ❌ preflight FAILED"
    fi
    exit "$rc"
fi
