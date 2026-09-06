---
name: git-amirulcyber
description: Manage GitHub repositories over HTTPS using a Personal Access Token (PAT). Provides session-scoped Git configuration for the Pi agent.
---

# git-amirulcyber

Use this skill for Git operations for the configured GitHub account using a PAT.

## Fixed configuration

- Authentication: GitHub Personal Access Token (PAT)
- Repository URL pattern: `https://github.com/<owner>/<repo>.git`
- GitHub CLI (`gh`): `/workspace/.local/bin/gh` or system `gh`
- Committer Identity: Scoped to session variables, defaults to Pi agent identity.

## Setup

Set up your PAT in the environment file:
`echo "GH-PAT-PI=<your_token>" > /home/johnn/piworkspace/pi-skills/git-amirulcyber/.env`

## Known gaps


The GitHub CLI is installed in a durable location:

- binary: `/workspace/.local/bin/gh` (durable, survives recreate)
- PATH symlink: `/home/appuser/.local/bin/gh` (first on PATH)

The helper script exports `GH_BIN` (durable binary first, then PATH). Source it once:

```bash
source "/workspace/dir-git-amirulcyber/opcd-skills/git-amirulcyber/scripts/git-env.sh"
```

To resolve `gh` manually:

```bash
GH_BIN="$(command -v gh || true)"
[ -n "$GH_BIN" ] || GH_BIN="/workspace/.local/bin/gh"
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
ENV_FILE="/workspace/dir-git-amirulcyber/opcd-skills/git-amirulcyber/.env"
printf 'GH-PAT-AMIRULCYBER-OPCD=%s\n' "YOUR_TOKEN_HERE" > "$ENV_FILE"
chmod 600 "$ENV_FILE"
```

The PAT must belong to the `amirulcyber` account and be able to create repositories:
- **Classic**: scope `repo`.
- **Fine-grained**: repository access "All repositories", permission **Administration:
  Read and write**.

Verify:

```bash
source "/workspace/dir-git-amirulcyber/opcd-skills/git-amirulcyber/scripts/git-env.sh"
"$GH_BIN" auth status
```

The helper tightens file permissions to 600 and exports `GH_TOKEN`, which survives
container recreates (unlike `gh auth login`, which writes to the ephemeral
`~/.config/gh`). Never print the token or commit it.

## SSH setup

Before any command that contacts GitHub, source the helper script. It resolves its own
location (works from any working directory) and exports `GIT_SSH_COMMAND` (pointing Git
at the bundled key only), `GH_BIN`, and the session-scoped committer identity
(`opcdamirulcyber <opcdamirulcyber@users.noreply.github.com>`):

```bash
source "/workspace/dir-git-amirulcyber/opcd-skills/git-amirulcyber/scripts/git-env.sh"
```

The helper resolves an `SSH_BIN` before anything else: first working `ssh` on
`PATH` (`ssh -V` must run), then `/workspace/.local/bin/ssh` (durable), then
`~/.local/bin/ssh`. `GIT_SSH_COMMAND` uses that absolute path, so git-over-SSH
no longer depends on ambient `PATH` — this fixed a session where no system
client existed (`cannot run ssh`). If no binary is found anywhere, sourcing
fails loud with install instructions instead of failing later at push time.
If you install one by hand (e.g. an extracted distro `openssh-client`), verify
its checksum against the signed package index first, and prefer the durable
`/workspace/.local/bin` so it survives recreates.

Manual fallback if the helper is unavailable:

```bash
export GIT_SSH_COMMAND="ssh -i \"/workspace/dir-git-amirulcyber/opcd-skills/git-amirulcyber/key_opencode_2026\" -o IdentitiesOnly=yes -o StrictHostKeyChecking=accept-new"
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
source "/workspace/dir-git-amirulcyber/opcd-skills/git-amirulcyber/scripts/git-env.sh"
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
source "/workspace/dir-git-amirulcyber/opcd-skills/git-amirulcyber/scripts/git-env.sh"
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
source "/workspace/dir-git-amirulcyber/opcd-skills/git-amirulcyber/scripts/git-env.sh"
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
source "/workspace/dir-git-amirulcyber/opcd-skills/git-amirulcyber/scripts/git-env.sh"
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
source "/workspace/dir-git-amirulcyber/opcd-skills/git-amirulcyber/scripts/git-env.sh"
git ls-remote "git@github.com:amirulcyber/$REPO_NAME.git"
```

If it exists, push:

```bash
git push -u origin main
```

If it does not exist, use the installed GitHub CLI to create the GitHub-side repository, then push the local `main` branch. Keep repository creation explicit and non-destructive. The default is **private** (see "Repository visibility policy"):

```bash
GH_BIN="${GH_BIN:-/workspace/.local/bin/gh}"
"$GH_BIN" repo create "amirulcyber/$REPO_NAME" --source=. --remote=origin --push --private
```

Use `--public` only after the user has explicitly requested public visibility and confirmed the final pre-creation warning. If the repository already exists, do not recreate it; configure/use the existing `origin` and push normally. The local repository creation must still be done with `git init` as requested.

## Authentication troubleshooting

Check SSH access without showing key material:

```bash
source "/workspace/dir-git-amirulcyber/opcd-skills/git-amirulcyber/scripts/git-env.sh"
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
