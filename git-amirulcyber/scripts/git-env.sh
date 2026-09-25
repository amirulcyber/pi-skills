#!/usr/bin/env bash
# git-env.sh — environment setup + preflight for the git-amirulcyber skill.
#
# Single source of truth for GitHub auth across hosts. Canonical location:
#   $SKILL_ROOT/git-amirulcyber/scripts/git-env.sh
# ($SKILL_ROOT = the pi-skills root — /workspace/pi-skills on neotokyo,
#  ~/piworkspace/pi-skills on saturn. Host table: ../AGENTS.md)
#
# SOURCE it to export the Git/gh environment for amirulcyber operations:
#   source "$SKILL_ROOT/git-amirulcyber/scripts/git-env.sh"
#
# RUN it standalone as a preflight self-test:
#   bash "$SKILL_ROOT/git-amirulcyber/scripts/git-env.sh" --check
#
# It never prints or exposes the private key or a token.

# ---------------------------------------------------------------------------
# Locate this skill (multi-host: never hardcode the repo path)
# ---------------------------------------------------------------------------
if [ -n "${BASH_SOURCE[0]:-}" ]; then
    GIT_AMIRULCYBER_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
else
    GIT_AMIRULCYBER_DIR="$(cd "$(dirname "$0")/.." && pwd)"
fi
export GIT_AMIRULCYBER_DIR
GIT_SKILLS_ROOT="$(cd "$GIT_AMIRULCYBER_DIR/.." && pwd)"
export GIT_SKILLS_ROOT

# Durable bin dir is a sibling of the skills root, so its value differs per host
# (neotokyo: /workspace/.local/bin, saturn: ~/.local/bin). Prepend each
# candidate that exists; a missing dir must never shadow PATH.
GIT_DURABLE_BIN="$(cd "$GIT_SKILLS_ROOT/.." && pwd)/.local/bin"
export GIT_DURABLE_BIN
for _bindir in "$GIT_DURABLE_BIN" "$HOME/.local/bin"; do
    if [ -d "$_bindir" ]; then
        _bindir="$(cd "$_bindir" && pwd)"
        case ":$PATH:" in
            *":$_bindir:"*) ;;
            *) PATH="$_bindir:$PATH" ;;
        esac
    fi
done
export PATH
unset _bindir

# ---------------------------------------------------------------------------
# Credentials: canonical = this skill dir; legacy = the old opencode tree.
# The legacy fallback exists only until the secrets are migrated here — see
# the "Migrating credentials" section of SKILL.md. Canonical paths are set
# FIRST, then overridden per file only when the canonical one is absent.
# ---------------------------------------------------------------------------
GIT_AMIRULCYBER_KEY="$GIT_AMIRULCYBER_DIR/key_opencode_2026"
GIT_AMIRULCYBER_ENV="$GIT_AMIRULCYBER_DIR/.env"
GIT_AMIRULCYBER_TOKEN="$GIT_AMIRULCYBER_DIR/gh_token"
export GIT_AMIRULCYBER_KEY GIT_AMIRULCYBER_ENV GIT_AMIRULCYBER_TOKEN

GIT_AMIRULCYBER_LEGACY_DIR="/workspace/dir-git-amirulcyber/opcd-skills/git-amirulcyber"
GIT_AMIRULCYBER_LEGACY_USED=""
for _f in key_opencode_2026 .env gh_token; do
    case "$_f" in
        key_opencode_2026) _canon="$GIT_AMIRULCYBER_KEY" ;;
        .env)             _canon="$GIT_AMIRULCYBER_ENV" ;;
        gh_token)         _canon="$GIT_AMIRULCYBER_TOKEN" ;;
    esac
    if [ ! -f "$_canon" ] && [ -f "$GIT_AMIRULCYBER_LEGACY_DIR/$_f" ]; then
        case "$_f" in
            key_opencode_2026) GIT_AMIRULCYBER_KEY="$GIT_AMIRULCYBER_LEGACY_DIR/$_f" ;;
            .env)             GIT_AMIRULCYBER_ENV="$GIT_AMIRULCYBER_LEGACY_DIR/$_f" ;;
            gh_token)         GIT_AMIRULCYBER_TOKEN="$GIT_AMIRULCYBER_LEGACY_DIR/$_f" ;;
        esac
        GIT_AMIRULCYBER_LEGACY_USED="$GIT_AMIRULCYBER_LEGACY_USED $_f"
    fi
done
unset _f _canon
[ -n "$GIT_AMIRULCYBER_LEGACY_USED" ] && \
    echo "git-amirulcyber: using LEGACY credential location ($GIT_AMIRULCYBER_LEGACY_USED) at $GIT_AMIRULCYBER_LEGACY_DIR — migrate into $GIT_AMIRULCYBER_DIR and this warning stops." >&2

# Tighten key permissions without exposing contents.
if [ -f "$GIT_AMIRULCYBER_KEY" ]; then
    chmod 600 "$GIT_AMIRULCYBER_KEY" 2>/dev/null || true
fi

# ---------------------------------------------------------------------------
# SSH client: first working `ssh` on PATH, then the known durable installs.
# A bare `ssh` in GIT_SSH_COMMAND broke git-over-SSH on machines with no
# system client ("cannot run ssh"), so always use an absolute path below.
# ---------------------------------------------------------------------------
if command -v ssh >/dev/null 2>&1 && ssh -V >/dev/null 2>&1; then
    SSH_BIN="$(command -v ssh)"
elif [ -x "$GIT_DURABLE_BIN/ssh" ]; then
    SSH_BIN="$GIT_DURABLE_BIN/ssh"
elif [ -x "$HOME/.local/bin/ssh" ]; then
    SSH_BIN="$HOME/.local/bin/ssh"
else
    SSH_BIN=""
fi
export SSH_BIN

if [ -z "$SSH_BIN" ]; then
    echo "git-amirulcyber: no working ssh client found (checked PATH, ${GIT_DURABLE_BIN}, ~/.local/bin)." >&2
    echo "  Install openssh-client, then re-source this file." >&2
    echo "  Without system packages: extract the official Debian openssh-client" >&2
    echo "  .deb (verify SHA256 against the signed Packages index) into ~/.local." >&2
    # In preflight mode keep going so --check reports every failure at once.
    if [ "${1:-}" != "--check" ] && [ "${1:-}" != "--selftest" ]; then
        if [ -n "${BASH_SOURCE[0]:-}" ] && [ "${BASH_SOURCE[0]}" != "$0" ]; then
            return 1 2>/dev/null || exit 1
        else
            exit 1
        fi
    fi
fi

# Git over SSH using only the bundled key.
export GIT_SSH_COMMAND="\"$SSH_BIN\" -i \"$GIT_AMIRULCYBER_KEY\" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"

# ---------------------------------------------------------------------------
# Committer identity — session-scoped (GIT_*_NAME/EMAIL override user.name/
# email without touching any git config), so the global config and other repos
# stay untouched. Pre-set values win, so a host can pick its own identity
# (saturn's Pi sessions use `pi-agent`) by exporting these before sourcing.
# ---------------------------------------------------------------------------
export GIT_AUTHOR_NAME="${GIT_AUTHOR_NAME:-opcdamirulcyber}"
export GIT_AUTHOR_EMAIL="${GIT_AUTHOR_EMAIL:-opcdamirulcyber@users.noreply.github.com}"
export GIT_COMMITTER_NAME="${GIT_COMMITTER_NAME:-opcdamirulcyber}"
export GIT_COMMITTER_EMAIL="${GIT_COMMITTER_EMAIL:-opcdamirulcyber@users.noreply.github.com}"

# ---------------------------------------------------------------------------
# GitHub CLI binary: durable install first, then PATH.
# ---------------------------------------------------------------------------
if [ -x "$GIT_DURABLE_BIN/gh" ]; then
    GH_BIN="$GIT_DURABLE_BIN/gh"
elif command -v gh >/dev/null 2>&1; then
    GH_BIN="$(command -v gh)"
else
    GH_BIN="gh"
fi
export GH_BIN

# ---------------------------------------------------------------------------
# GitHub API token for `gh repo create` (durable, survives recreate). The SSH
# key covers git-over-SSH only; the REST API needs a PAT. Order: ambient
# GH_TOKEN → .env (any known variable name) → gh_token. Both file paths may
# point at the legacy location — see the credentials block above.
# ---------------------------------------------------------------------------
if [ -z "${GH_TOKEN:-}" ]; then
    if [ -f "$GIT_AMIRULCYBER_ENV" ]; then
        chmod 600 "$GIT_AMIRULCYBER_ENV" 2>/dev/null || true
        for _var in GH-PAT-AMIRULCYBER-OPCD GH-PAT-AMIRULCYBER-PI GH-PAT-PI; do
            [ -n "${GH_TOKEN:-}" ] && break
            _gh_pat="$(sed -n "s/^${_var}=//p" "$GIT_AMIRULCYBER_ENV" | head -n1 | tr -d '[:space:]' || true)"
            [ -n "$_gh_pat" ] && GH_TOKEN="$_gh_pat"
        done
        unset _var
    fi
    if [ -z "${GH_TOKEN:-}" ] && [ -s "$GIT_AMIRULCYBER_TOKEN" ]; then
        chmod 600 "$GIT_AMIRULCYBER_TOKEN" 2>/dev/null || true
        GH_TOKEN="$(head -n1 "$GIT_AMIRULCYBER_TOKEN" | tr -d '[:space:]' || true)"
    fi
    [ -n "${GH_TOKEN:-}" ] && export GH_TOKEN
fi

# ---------------------------------------------------------------------------
# Preflight self-test (run with --check / --selftest)
# ---------------------------------------------------------------------------
if [ "${1:-}" = "--check" ] || [ "${1:-}" = "--selftest" ]; then
    rc=0

    echo "=== git-amirulcyber preflight ==="
    echo "  skills root: $GIT_SKILLS_ROOT"
    echo "  identity: $GIT_AUTHOR_NAME <$GIT_AUTHOR_EMAIL> (session-scoped)"

    if [ -f "$GIT_AMIRULCYBER_KEY" ]; then
        echo "  ✅ private key present ($GIT_AMIRULCYBER_KEY)"
    else
        echo "  ❌ private key MISSING: $GIT_AMIRULCYBER_KEY"
        rc=1
    fi

    # ssh client binary (git-over-SSH is dead without it — bare `ssh`
    # previously failed with "cannot run ssh" on client-less machines)
    if [ -n "${SSH_BIN:-}" ] && [ -x "$SSH_BIN" ]; then
        echo "  ✅ ssh binary: $SSH_BIN ($("$SSH_BIN" -V 2>&1 | head -n1))"
    else
        echo "  ❌ ssh binary not found (checked PATH, $GIT_DURABLE_BIN, ~/.local/bin)"
        rc=1
    fi

    # gh binary
    if command -v "$GH_BIN" >/dev/null 2>&1; then
        echo "  ✅ gh binary: $GH_BIN"
    else
        echo "  ❌ gh binary not found (expected $GIT_DURABLE_BIN/gh, or gh on PATH)"
        rc=1
    fi

    # SSH auth. GitHub returns exit 1 even on success (no shell access),
    # so judge on the message, not the exit code.
    if [ -n "${SSH_BIN:-}" ] && [ -x "$SSH_BIN" ]; then
        ssh_out="$("$SSH_BIN" -i "$GIT_AMIRULCYBER_KEY" -o IdentitiesOnly=yes \
            -o StrictHostKeyChecking=accept-new -o BatchMode=yes \
            -T git@github.com 2>&1 || true)"
    else
        ssh_out=""
    fi
    if echo "$ssh_out" | grep -q "successfully authenticated"; then
        user="$(echo "$ssh_out" | sed -n 's/.*Hi \(.*\)! You.*/\1/p')"
        echo "  ✅ SSH auth: OK (authenticated as $user)"
    else
        echo "  ❌ SSH auth: FAILED"
        echo "$ssh_out" | sed 's/^/       /'
        rc=1
    fi

    # gh API auth (required only for gh repo create, not for git-over-SSH)
    if "$GH_BIN" auth status >/dev/null 2>&1; then
        echo "  ✅ gh API auth: OK"
    else
        echo "  ⚠️  gh API auth: NOT logged in — 'gh repo create' needs a PAT in $GIT_AMIRULCYBER_ENV — see SKILL.md"
    fi

    echo ""
    if [ "$rc" -eq 0 ]; then
        echo "  ✅ preflight passed"
    else
        echo "  ❌ preflight FAILED"
    fi
    exit "$rc"
fi
