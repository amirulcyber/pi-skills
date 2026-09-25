---
name: git-amirulcyber
description: Manage GitHub repositories for the amirulcyber account over SSH (bundled key) plus the REST API (PAT), with session-scoped git identity. Provides the single git/gh environment helper for both hosts (neotokyo opencode container, saturn Pi VM). Use for any Git or gh operation on a repo under amirulcyber.
---

# git-amirulcyber

Use this skill for Git operations for the configured GitHub account.

**Single source of truth.** `$SKILL_ROOT/git-amirulcyber/` holds the helper,
the docs, and the credentials. The old
`~/piworkspace/dir-git-amirulcyber/opcd-skills/git-amirulcyber/` tree is
**deprecated** — source this skill's `git-env.sh`; it falls back to the old
location for credentials only until they are migrated (see below), and prints a
warning on stderr while that fallback is in use.

## Fixed configuration

- Git transport: SSH with the bundled key only (`IdentitiesOnly=yes`)
- API transport: PAT (`gh repo create` and other REST calls need it; the SSH key
  does not cover the API)
- Repository URL pattern: `git@github.com:amirulcyber/<repo>.git`
- Committer identity: session-scoped (`GIT_*_NAME`/`GIT_*_EMAIL`), never a
  global git config change

**Host-dependent paths.** `git-env.sh` resolves every path from its own
location, so the same command works on both hosts — the table below is for
reading, not for typing. Resolve the host from the marker-file table in
`../AGENTS.md` (no `hostname` call needed).

| What | neotokyo (opencode container) | saturn (Pi VM) |
|---|---|---|
| `SKILL_ROOT` | `~/piworkspace/pi-skills` | `~/piworkspace/pi-skills` |
| Durable `gh` | `~/piworkspace/.local/bin/gh` | `~/.local/bin/gh` or system `gh` |
| `GIT_ENV` | `$SKILL_ROOT/git-amirulcyber/scripts/git-env.sh` | same path, different `SKILL_ROOT` |
| Default identity | `pi-agent` | `pi-agent` — one identity on both hosts (owner decision 2026-09-25). Export `GIT_AUTHOR_*`/`GIT_COMMITTER_*` before sourcing to override. Attribution only; auth is the bundled `amirulcyber` key on both. |

## Setup

Credentials live **next to `git-env.sh`**, in its own skill dir:

| File | Holds | Gitignored |
|---|---|---|
| `key_opencode_2026` (+ `.pub`) | SSH private key for git-over-SSH | private key yes, `.pub` no |
| `.env` | `GH-PAT-AMIRULCYBER-OPCD` (fine-grained, admin — can create repos), or `GH-PAT-AMIRULCYBER-PI` / `GH-PAT-PI` | yes |
| `gh_token` | bare PAT, first line; fallback if `.env` has none | yes |

`git-env.sh` checks them in that order and never prints a key or token. Load
order for the token: ambient `GH_TOKEN` → `.env` (first recognised variable
name) → `gh_token`.

```bash
# once, per host
printf 'GH-PAT-AMIRULCYBER-OPCD=%s\n' "YOUR_TOKEN" > "$SKILL_ROOT/git-amirulcyber/.env"
chmod 600 "$SKILL_ROOT/git-amirulcyber/.env"
```

## Copying credentials into this skill dir (per host, one-off)

The helper reads `key_opencode_2026` / `.env` / `gh_token` from this skill dir
first, and only falls back to the deprecated tree
(`~/piworkspace/dir-git-amirulcyber/opcd-skills/git-amirulcyber/`, resolved
relative to the skills root) when a file is missing here — warning on stderr
while it does. **Each host needs its own copy.** neotokyo's was migrated
2026-09-25 (preflight passes with no warning); saturn's is still outstanding.

To finish the move on a host, copy the files across (never `cat` — the key must
not hit a transcript) and re-run the preflight:

```bash
cd ~/piworkspace
cp -p dir-git-amirulcyber/opcd-skills/git-amirulcyber/key_opencode_2026  pi-skills/git-amirulcyber/
cp -p dir-git-amirulcyber/opcd-skills/git-amirulcyber/key_opencode_2026.pub pi-skills/git-amirulcyber/
cp -p dir-git-amirulcyber/opcd-skills/git-amirulcyber/.env             pi-skills/git-amirulcyber/
[ -f dir-git-amirulcyber/opcd-skills/git-amirulcyber/gh_token ] && \
  cp -p dir-git-amirulcyber/opcd-skills/git-amirulcyber/gh_token       pi-skills/git-amirulcyber/
chmod 600 pi-skills/git-amirulcyber/key_opencode_2026 pi-skills/git-amirulcyber/.env
bash pi-skills/git-amirulcyber/scripts/git-env.sh --check   # warning must be gone
```

`.gitignore` already ignores `key_opencode_2026`, `.env`, and `gh_token`, so
the copy cannot be committed — verify with `git check-ignore` before committing
anything in that dir. Once the preflight is clean, the deprecated tree can go.

## `gh` binary location

`gh` lives in the host's durable bin dir, which is why the helper resolves it
rather than hardcoding one:

- neotokyo: `~/piworkspace/.local/bin/gh` (survives a container recreate), with
  the mise shim `~/.local/bin/gh` first on PATH
- saturn: `~/.local/bin/gh` or the system `gh` (2.46.0)

The helper script exports `GH_BIN` (durable binary first, then PATH). Source it once:

```bash
source "$SKILL_ROOT/git-amirulcyber/scripts/git-env.sh"
```

To resolve `gh` manually:

```bash
GH_BIN="$(command -v gh || true)"
[ -n "$GH_BIN" ] || GH_BIN="$HOME/piworkspace/.local/bin/gh"   # neotokyo durable path
```

Before GitHub-side API operations such as `gh repo create`, verify CLI authentication:

```bash
"$GH_BIN" auth status
```

Do not print authentication tokens or other credentials.

## GitHub API authentication (`gh repo create`)

`gh repo create` calls the GitHub REST API, which needs a Personal Access Token (PAT) —
the SSH key does not cover the API. The PAT is stored durably and loaded by the helper.

**Location:** `<skill-root>/.env` — variable `GH-PAT-AMIRULCYBER-OPCD` (fine-grained PAT,
`github_pat_...`). The helper reads it automatically. If `.env` is absent, the helper
falls back to `<skill-root>/gh_token` (bare token on the first line).

To add or rotate the token:

```bash
ENV_FILE="$SKILL_ROOT/git-amirulcyber/.env"
printf 'GH-PAT-AMIRULCYBER-OPCD=%s\n' "YOUR_TOKEN_HERE" > "$ENV_FILE"
chmod 600 "$ENV_FILE"
```

The PAT must belong to the `amirulcyber` account and be able to create repositories:
- **Classic**: scope `repo`.
- **Fine-grained**: repository access "All repositories", permission **Administration:
  Read and write**.

Verify:

```bash
source "$SKILL_ROOT/git-amirulcyber/scripts/git-env.sh"
"$GH_BIN" auth status
```

The helper tightens file permissions to 600 and exports `GH_TOKEN`, which survives
container recreates (unlike `gh auth login`, which writes to the ephemeral
`~/.config/gh`). Never print the token or commit it.

## SSH setup

Before any command that contacts GitHub, source the helper script. It resolves its own
location (works from any working directory) and exports `GIT_SSH_COMMAND` (pointing Git
at the bundled key only), `GH_BIN`, and the session-scoped committer identity
(`pi-agent <pi-agent@users.noreply.github.com>`):

```bash
source "$SKILL_ROOT/git-amirulcyber/scripts/git-env.sh"
```

The helper resolves an `SSH_BIN` before anything else: first working `ssh` on
`PATH` (`ssh -V` must run), then the host's durable bin dir
(`$GIT_DURABLE_BIN` — `~/piworkspace/.local/bin` on neotokyo), then
`~/.local/bin/ssh`. `GIT_SSH_COMMAND` uses that absolute path, so git-over-SSH
no longer depends on ambient `PATH` — this fixed a session where no system
client existed (`cannot run ssh`). If no binary is found anywhere, sourcing
fails loud with install instructions instead of failing later at push time.
If you install one by hand (e.g. an extracted distro `openssh-client`), verify
its checksum against the signed package index first, and prefer the host's
durable bin dir so it survives recreates.

Manual fallback if the helper is unavailable:

```bash
export GIT_SSH_COMMAND="ssh -i \"$SKILL_ROOT/git-amirulcyber/key_opencode_2026\" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
```

The helper also tightens the key permissions to 600 without displaying the key.

## Safety rules

- Do not reveal the private key or any derived secret material.
- Do not force-push, reset hard, delete branches, rewrite history, or remove untracked files unless the user explicitly requests that destructive action.
- Before commit or push, run `git status --short` and review the changed paths.
- Do not commit obvious secrets such as `.env`, private keys, tokens, credentials, or credential dumps. If detected, stop and warn the user.
- Preserve unrelated local changes.
- Use normal `git pull --ff-only` by default to avoid accidental merge commits.
- Quote paths and branch names in shell commands.

## Repository selection

When the user names a repository `NAME`, use:

```bash
REPO_URL="git@github.com:amirulcyber/NAME.git"
```

For “the blog”, “Amirul Cyber blog”, or the website repo, use:

```bash
REPO_URL="git@github.com:amirulcyber/amirulcyber.github.io.git"
```

## Clone a repository

```bash
source "$SKILL_ROOT/git-amirulcyber/scripts/git-env.sh"
git clone "$REPO_URL"
```

If a destination directory is supplied:

```bash
git clone "$REPO_URL" "$DEST"
```

## Inspect current state

Run these before making changes:

```bash
git status --short
git branch --show-current
git remote -v
```

Optionally inspect recent history:

```bash
git log --oneline -n 10
```

## Update an existing checkout

```bash
source "$SKILL_ROOT/git-amirulcyber/scripts/git-env.sh"
git fetch --prune origin
git pull --ff-only
```

If the working tree has local modifications, do not overwrite or stash them automatically unless the user asks.

## Create or switch branches

Create a new branch:

```bash
git switch -c "$BRANCH"
```

Switch to an existing branch:

```bash
git switch "$BRANCH"
```

## Commit changes

Before committing:

```bash
git status --short
git diff --check
git diff
```

Stage only the intended files when practical:

```bash
git add -- path/to/file1 path/to/file2
git status --short
git commit -m "$MESSAGE"
```

Use `git add -A` only when the user intends all current changes to be committed.

## Push changes

For a branch already tracking a remote:

```bash
source "$SKILL_ROOT/git-amirulcyber/scripts/git-env.sh"
git push
```

For a new branch:

```bash
git push -u origin "$BRANCH"
```

Never use `--force` or `--force-with-lease` unless explicitly requested.

## Blog workflow

For the Amirul Cyber blog:

```bash
source "$SKILL_ROOT/git-amirulcyber/scripts/git-env.sh"
git clone git@github.com:amirulcyber/amirulcyber.github.io.git
cd amirulcyber.github.io
git status --short
```

After edits, inspect, commit, and push using the normal workflow above.

## Create a new repository when requested

Use Git commands to create the local repository:

```bash
mkdir -p "$REPO_NAME"
cd "$REPO_NAME"
git init --initial-branch=main
```

Add initial files as requested, then commit:

```bash
git add -- <files>
git commit -m "Initial commit"
```

Configure the expected GitHub remote:

```bash
git remote add origin "git@github.com:amirulcyber/$REPO_NAME.git"
```

Then test whether the GitHub repository already exists:

```bash
source "$SKILL_ROOT/git-amirulcyber/scripts/git-env.sh"
git ls-remote "git@github.com:amirulcyber/$REPO_NAME.git"
```

If it exists, push:

```bash
git push -u origin main
```

If it does not exist, use the installed GitHub CLI to create the GitHub-side repository, then push the local `main` branch. Keep repository creation explicit and non-destructive. The default is **private** (see "Repository visibility policy"):

```bash
GH_BIN="${GH_BIN:-$HOME/piworkspace/.local/bin/gh}"
"$GH_BIN" repo create "amirulcyber/$REPO_NAME" --source=. --remote=origin --push --private
```

Use `--public` only after the user has explicitly requested public visibility and confirmed the final pre-creation warning. If the repository already exists, do not recreate it; configure/use the existing `origin` and push normally. The local repository creation must still be done with `git init` as requested.

## Authentication troubleshooting

Check SSH access without showing key material:

```bash
source "$SKILL_ROOT/git-amirulcyber/scripts/git-env.sh"
ssh -T git@github.com
```

GitHub may return a non-zero exit status even when authentication succeeds; read the message rather than relying only on the exit code.

For verbose troubleshooting only when necessary:

```bash
GIT_SSH_COMMAND="$GIT_SSH_COMMAND -v" git ls-remote "$REPO_URL"
```

Do not paste private key material into diagnostics.

## Completion report

After performing a Git task, report concisely:

- repository and branch
- files changed or committed
- commit hash, if a commit was created
- push result / remote tracking branch
- any unresolved authentication or remote-existence issue

## Repository visibility policy

- **Private is mandatory by default.** Every newly created GitHub repository MUST be created as private unless the user explicitly requests public visibility.
- Before creating a new repository, determine the requested visibility:
  - No visibility specified → use **private** without asking.
  - User explicitly requests **public** → **do not create yet**. State clearly that the repository will be public and ask for a final confirmation immediately before creation. Only proceed after an explicit confirmation such as "yes", "confirm", or equivalent.
  - User explicitly requests **private** → create private without an additional confirmation.
- After creating a repository, **validate its visibility** using GitHub CLI: `gh repo view OWNER/REPO --json visibility,isPrivate`. The expected result for the default workflow is `PRIVATE` / `isPrivate: true`.
- If validation shows the repository is not private when private was required, stop and report the mismatch. Do not continue with pushes or other irreversible operations until the visibility issue is resolved.
- For an explicitly confirmed public repository, validate that the resulting visibility is `PUBLIC` / `isPrivate: false` before continuing.
- Never infer permission to make a repository public from context, an existing public repository, or a command template. Public creation requires an explicit user request **and** a final confirmation.

### Creation examples

Default private creation:

```bash
gh repo create "$OWNER/$REPO" --private --source=. --remote=origin --push
gh repo view "$OWNER/$REPO" --json visibility,isPrivate
```

The validation must report `PRIVATE` and `isPrivate: true`.

For a public repository, only after the user has explicitly requested public visibility and then explicitly confirmed the final pre-creation warning:

```bash
gh repo create "$OWNER/$REPO" --public --source=. --remote=origin --push
gh repo view "$OWNER/$REPO" --json visibility,isPrivate
```

The validation must report `PUBLIC` and `isPrivate: false`.
