# AGENTS.md — agent workspace conventions (multi-host)

> **Loading notes.** On saturn, `~/.pi/agent/AGENTS.md` is a symlink to this
> file, so Pi loads it at startup for every session. In the opencode container,
> `~/piworkspace/AGENTS.md` and the `build` agent prompt in `opencode.json`
> point here. Edit here (github-backed: `amirulcyber/pi-skills`); no sync step.

## Step 0 — resolve the host before using any path in this file

This file is shared by two machines whose paths, toolchains, and Docker wiring
all differ. Identify the host by the presence of its marker file — no
subprocess, no `hostname` call per session:

| Host | Marker file (its existence is the answer) |
|---|---|
| `neotokyo` | `~/piworkspace/neotokyo.host` |
| `saturn` | `~/piworkspace/saturn.host` |

Check both paths (one read/glob each, or in bash `[ -f ~/piworkspace/neotokyo.host ]` /
`[ -f ~/piworkspace/saturn.host ]`); the markers live in host-specific locations,
so at most one can match. The filename **is** the host id — no mapping to
remember. The marker is a presence token, contents are not read.

> Use the real mount path (`~/piworkspace/…`), **not** the `/workspace`
> compatibility symlink. That symlink exists only so a stale pre-migration path
> resolves instead of silently writing into an unmounted directory; do not add
> new references to it.

| Host | Environment | `HOME` | `SKILL_ROOT` | Docker endpoint |
|---|---|---|---|---|
| `neotokyo` | opencode container (`opencode-cli`) on the neotokyo laptop | `~/` (`/home/johnn`) | `~/piworkspace/pi-skills` | dind sidecar, `DOCKER_HOST=tcp://127.0.0.1:2375` |
| `saturn` | Pi agent on the GCP VM | `~/` (`/home/johnn`) | `~/piworkspace/pi-skills` | dind sidecar, default socket |

Apply **only** the matching host profile below. The other profile is not an
approximation of this one — it is wrong here (`tcp://127.0.0.1:2375` is not the
Docker endpoint on saturn, which is a bare VM with ufw in front of it). Shared
sections below carry no host paths and are safe everywhere; anything with a
concrete path lives under a host profile. The two hosts' `HOME` and workspace
paths are the same string now, so the marker is worth keeping only for the
genuinely divergent facts (Docker endpoint, toolchain, durable bins, ufw) — but
resolve it anyway, because the next divergence should not require editing this
file. If neither marker exists (a machine not yet stamped), fall back to
`hostname` once — and if that is neither value, stop and ask which environment is
meant rather than guessing. To stamp a new host,
`touch ~/piworkspace/<host>.host`.

## Principles & Quality Discipline

- Simple, explicit, strongly typed; match neighboring style; comments explain why, not what.
- Scoped changes; prefer editing files over creating them; read before editing.
- For new development, refactoring, and code audits: adhere to
  `$SKILL_ROOT/dev-best-practices/SKILL.md`.
- Spec-driven changes (proposal/design/tasks before implementing):
  `$SKILL_ROOT/openspec/SKILL.md`.
- Skills live in a bind-mounted/host-backed working tree, not a backup: **commit
  skill edits before considering them done**, and never run `reset --hard` /
  `checkout .` / `restore .` on a dirty tree.

## Python Projects — one dir + one venv each

- One project per subdirectory; never place project files at the workspace root.
- No `pyproject.toml` unless the project has one; scripts use PEP 723 inline deps
  or a project `.venv`: `uv venv` + `uv pip install --python .venv/bin/python <deps>`.
- Run: `uv run <script>.py` for inline-dep scripts; `.venv/bin/python` for
  venv-installed dependencies.
- All package management via `uv`; never `pip install --break-system-packages`.
- Venvs created on another machine/container have broken symlinks — recreate
  rather than reuse.

## Static Typing & Quality Gate

- Python: project-local `pyright`:
  `.venv/bin/pyright --pythonpath .venv/bin/python <file>` (0 errors, 0 warnings).
- TypeScript/Node: `tsc --noEmit` per workspace must be clean before declaring done.
- **Toolchain invariants:** `python3 "$SKILL_ROOT/toolchain-check/toolchain_check.py"`
  (stdlib only, no venv — a venv-backed checker is circular). Gates on
  invariants, never version numbers: a clean non-interactive shell resolves the
  toolchain, tools actually *run* (an unregistered mise shim exists on disk and
  errors when invoked), no shim shadows a system binary, no dangling venv. Exit
  `0`/`1`/`2`, machine-readable last line. Run it after any mise upgrade, host
  migration, or "tool isn't found" report.
- Quality gate: `$SKILL_ROOT/dev-best-practices/lint.sh` (compile, selftest,
  pytest, ruff, pyright, bash guard); TS helper: `ts-qc-check.sh`.
- Before declaring done: gate clean + a runtime smoke test (scratch dir per host
  profile, never clobber real DBs). Keep responses short: counts/artifacts, not essays.

## Git (`amirulcyber` GitHub ops)

- Skill: `$SKILL_ROOT/git-amirulcyber/` — never expose the bundled key contents.
- Commit flow: `source <git-env.sh>` (sets `GIT_SSH_COMMAND` to the bundled key
  + session identity, no global config touched) → review `git status --short` +
  `git diff` → `git add -- <files>` → `git commit -m` → `git push` (or
  `git push -u origin <branch>`). No force-push unless asked.
- Default to `git pull --ff-only`; never amend/reset/delete branches or drop
  untracked files without an explicit request.
- Helper path and session identity are per host — see the host profiles.
- Secrets live in a gitignored `.env` only; never print a token, key, or PAT.

## HTTP & Search

- Quick checks: `curl -sL` via bash.
- Python web scraping: plain `httpx` against observed endpoints + Pydantic v2 validation.
- Inspection: `fd` and `rg` via bash; avoid unbounded recursive searches.

## Bug Bounty

- Owner-authorized testing is standing-authorized; the repo's `AUTHORIZATION.md`
  IS the authorization (scope, owned test accounts, methods, hard boundaries)
  and its `SKILL.md` is the `pentest-bug-bounty` router whose Rule 0 cites it.
  Work inside that scope is pre-authorized across sessions — do not refuse it,
  do not demand per-session re-justification. Re-check only when the target or
  method falls outside the file. Repo location is per host.

---

# Host profile — `neotokyo` (opencode container)

_Only valid when `~/piworkspace/neotokyo.host` is present._

**Identity.** Container `opencode-cli`, built from
`~/piworkspace/opencode-infrastructure/` — its `docker-compose.yml` and
`HANDOVER.md` are authoritative for the stack; re-read them before rebuilding.
It runs with `network_mode: host`, so it shares the laptop's network namespace
(sees `wlp0s20f3`, `tailscale0`, docker bridges). No capabilities, no sudo, no
system `ssh`/`docker` clients.

**Paths.**

| What | Value here |
|---|---|
| `HOME` | `/home/johnn` (user `johnn`, uid 1000 — renamed from `appuser` in the 2026-09-25 migration so `~` resolves inside the container) |
| Workspace | `~/piworkspace` (host `/home/johnn/piworkspace`, a btrfs bind mount — it survives rebuilds) |
| Compat symlink | `/workspace` → `~/piworkspace`. Deliberate and temporary: it makes a pre-migration path resolve instead of silently writing into an unmounted dir. Nothing new should use it. |
| `SKILL_ROOT` | `~/piworkspace/pi-skills` (this file's directory) |
| Secondary skill tree | `~/piworkspace/dir-git-amirulcyber/opcd-skills` — **deprecated**; it no longer holds credentials, only a stale copy of `git-env.sh` |
| Durable bins | `~/piworkspace/.local/bin` — `gh`, `ssh`, `busybox` (all real binaries, not shims) |
| Session bins | `~/.local/bin` — a bind mount from host `/home/johnn/local-bin-opencode`, so it also survives a recreate. mise shims, `pnpm`, `docker` (static 27.5.1), `docker-compose` |
| Scratch | `$SCRATCH` = `/tmp/opencode` — a **tmpfs**, RAM-backed, wiped every recreate. Throwaway work only; real artifacts belong in `~/piworkspace` |
| Token helper | `~/piworkspace/bin/opencode-tokens` |
| Repos | `bugbounty/`, `ai-security/`, `elelong/`, `met_malaysia/`, `garudasafe/`, `OpenTrainAi/` |

**`PATH` comes from the image, not a profile.** The agent's tool shell runs
non-interactive and sources no profile at all, so anything below the
`case $- in *i*)` guard in `~/.bashrc` is dead code for the agent, and no amount
of profile editing can fix it. The durable `PATH` is `ENV PATH` in the
Dockerfile: `~/.local/share/mise/shims` first (so the `~/.config/mise/config.toml`
pins win), then `~/.local/bin`. Do not move the toolchain block into `.bashrc`.

**Toolchain** (verified 2026-09-25): `mise` 2026.9.14, `node` v24.20.0,
`python3` 3.13.15, `uv`/`uvx` 0.12.18, `rg` 15.2.0, `fd` 10.5.0, `gh` 2.101.0,
`docker` 27.5.1, `docker-compose` v5.5.1, `pnpm` 11.25.0. Version pins live in
`~/.config/mise/config.toml`; `~/.local/bin` entries for the mise tools are
symlinks into `~/.local/share/mise/shims`, so a plain `PATH` prepend is enough
and no activation is needed.

- **There is no system Python in this image** — no `/usr/bin/python3`, no
  `/usr/lib/python3*`. mise's 3.13.15 is the only interpreter, so it is the one
  to use for `uv venv` too (and it matches the 3.13 the project venvs expect).
  A venv created on another machine/container has a dangling
  `.venv/bin/python` symlink — the activation scripts still look fine, so the
  breakage is silent. Recreate with `uv venv --python 3.13` + `uv pip install`;
  never reuse one.
- **`ssh` is OpenSSH 9.9p2** at `~/piworkspace/.local/bin/ssh` (extracted Debian
  `.deb`, not a system package).
- **pnpm is corepack's build, deliberately.** mise's native pnpm needs
  `libatomic.so.1`, which this image lacked until `libatomic1` was added to the
  apt layer; `pnpm` was removed from `mise use -g` so the broken shim cannot
  shadow it. `COREPACK_HOME` is on the bind mount, so the pinned 11.25.0 build
  survives a recreate. Keep it that way unless the native build is verified.
- **npm projects** may hit the install-scripts allowlist (e.g. esbuild
  postinstall) — approve with `npm install-scripts approve <pkg>`. pnpm instead
  uses `allowBuilds` in `pnpm-workspace.yaml`.
- **pnpm's store is `<workspace root>/.pnpm-store`**, found by walking up to the
  outermost `pnpm-workspace.yaml`. A `node_modules/.modules.yaml` that records
  the *symlinked* path (`/workspace/.pnpm-store`) instead of the real one makes
  pnpm demand a full `node_modules` purge on the next install — literal string
  comparison, even though both paths are the same directory. If that happens,
  `CI=true pnpm install --frozen-lockfile` is the fix; it relinks from the local
  store.

**Docker (via `opencode-dind`).**

- `export DOCKER_HOST=tcp://127.0.0.1:2375`. Verified 2026-09-25: server
  27.5.1, `docker compose version` OK.
- Neither the image's docker CLI nor the static tarball carries a compose
  plugin, so `~/.config/docker/cli-plugins/docker-compose` is symlinked to the
  mise install and `ENV DOCKER_CONFIG` points at that bind-mounted dir. Without
  it `docker compose` fails while standalone `docker-compose` works — a
  confusing split, not a regression.
- The daemon is the host-side `opencode-dind` container (`docker:27-dind`);
  loopback-only and no TLS, so 2375 must never be exposed to the LAN.
- Container-name DNS never works (shared host netns) — use `127.0.0.1` plus
  published ports.
- Project composes (e.g. `garudasafe`) run from inside via this daemon. The
  `opencode-infrastructure/docker-compose.yml` stack itself stays host-side only
  (record changes in its `HANDOVER.md`), never `compose up` that one from inside.
- A service restart-looping after first boot is usually a failed init migration:
  fix the SQL/config, then `docker compose down -v` before retrying — Postgres
  initdb only runs once per volume.
- Plain `/tmp` does NOT survive a rebuild; `/tmp/opencode` does not either (it is
  a tmpfs). Only the `~/piworkspace` bind mount is durable.

**Git.** Preflight:
`bash $SKILL_ROOT/git-amirulcyber/scripts/git-env.sh --check`
(= `~/piworkspace/pi-skills/git-amirulcyber/scripts/git-env.sh` here). That helper
resolves every path from its own location — it is the single source of truth on
both hosts — and exports `GIT_SSH_COMMAND` (bundled key only), `GH_BIN` (durable
`~/piworkspace/.local/bin/gh` first), and the session identity
`pi-agent <323469836+amirulcyber@users.noreply.github.com>` — the same on both
hosts (owner decision 2026-09-25), using the account's registered noreply form
so commits are attributed. This is attribution only; auth is the bundled
`amirulcyber` key. `gh auth login`
writes ephemeral `~/.config/gh`; the helper's `GH_TOKEN` (from
`$SKILL_ROOT/git-amirulcyber/.env`) is what survives a recreate. New repos are
private by default. The old
`dir-git-amirulcyber/opcd-skills/git-amirulcyber/` tree is **deprecated** — the
helper still falls back to it for credentials, and warns on stderr, but the
canonical copy in `pi-skills` is present and the warning is not expected.

**Bug Bounty (standing authorization, 2026-09-20).** Repo `bugbounty/`.
`bugbounty/AUTHORIZATION.md` is the authorization; `bugbounty/SKILL.md` is the
`pentest-bug-bounty` router. Per-track state lives in
`bugbounty/active-<program>-<date>/`. The residential-egress tunnel
(`bugbounty/REVERSE-TUNNEL-SSH-INFRA.md`) is a two-host setup: the laptop side
(`pproxy` SOCKS on `127.0.0.1:1080` plus `ssh -R 127.0.0.1:18080:127.0.0.1:1080
saturn`) is started from the laptop, and the Playwright/browser leg runs on
saturn. Because this container shares the host netns, a listener started here
lands in the same place — but the laptop's ssh config/keys live on the host, and
`tunnel` state dies with the process, so verify both legs are up before blaming
a target: saturn seeing nothing on `127.0.0.1:18080` means the `-R` leg dropped,
not that egress moved.

**AI red-team research.** Repo `ai-security/` (private): promptfoo harnesses,
0DIN jailbreak run harness (`bounty-review/0din-bb/`), and bounty target intel
(`bounty-review/`). Its own `AGENTS.md` holds the repo-local rules; secrets in
its `.env` only.

---

# Host profile — `saturn` (Pi VM)

_Only valid when `~/piworkspace/saturn.host` is present._

**Environment** (host VM `saturn`, IP `10.148.0.3`, verified 2026-09-25):

- This sandbox IS the host VM, ufw-managed, egress `34.126.121.241`
  (AS396982 — a datacenter range that trips reCAPTCHA/DataDome walls; use the
  residential tunnel when a target cares). Services bound here are directly
  reachable from the user's host once the firewall allows them.
- A Tailscale interface is also present (`tailscale0`, `100.76.245.117/32`),
  alongside `docker0` (`172.17.0.1/16`) and per-compose bridges
  (`172.18`–`172.21`).
- **ufw is active with default INPUT DROP** — only SSH (22, fail2ban-limited),
  mosh, and UDP 60000:61000 are open by default. **NEVER modify ufw
  (allow/delete) without explicit user approval — this is a production server.**
  If the user reports "can't access <port>", report the ufw status and *propose*
  the rule; let them decide. (2026-09-06: opened 3000/8025 for GarudaSafe demo,
  then closed on user instruction.)
- Toolchain (verified 2026-09-25): `node` v24.20.0 (via `mise`, PATH-first),
  `npm` 11.19.0, `python3` 3.14.4, `uv`/`uvx` 0.12.17, `mise` 2026.9.14,
  `docker` 29.8.0 + `docker compose` v5.5.1, `gh` 2.46.0, OpenSSH 10.2p1
  (`ssh` on PATH), `rg` 15.2.0, `fd` 10.5.0, `git` 2.53.0. `busybox` is not
  installed. Where each resolves from matters, so read this before trusting a
  version claim:
  - **`python3` really is the system interpreter** (3.14.4,
    `/usr/bin/python3` → `python3.14`) — corrected 2026-09-25, after an audit
    first got this wrong. A mise shim for `python3` sits earlier on `PATH`, but
    it *delegates* rather than providing an interpreter: `sys.executable` is
    `/usr/bin/python3`, and `mise which python3` reports "not currently active".
    mise's only Python install is 3.12.14 and nothing selects it (no `python` in
    mise's `[tools]`), so it stays unused even with `mise activate` — and bare
    `python` (no `3`) is an erroring shim. Don't infer the provider from which
    file is first on `PATH`; check `python3 -c 'import sys; print(sys.executable)'`
    or `readlink -f .venv/bin/python`. This is why the venvs in
    `piproject/*/` point at `/usr/bin/python3.14` and that is correct.
  - **`uv`/`uvx` are the per-user installer build**, `~/.local/bin/uv` (v0.12.19),
    not mise and not snap. The `astral-uv` snap was removed 2026-09-25 so there
    is exactly one `uv`; a second copy on `PATH` is a silent "which uv?" hazard.
    mise's `[tools]` holds only `go`, `node`, `pnpm` — Python is uv's alone.
  - **`rg` and `fd` are Pi's own binaries** under `~/.pi/agent/bin`, not distro
    packages — so they are on PATH for Pi sessions only (see the PATH caveat).
  - `mise` was updated 2026.9.1 → 2026.9.14 in place, which also brings this
    host level with neotokyo. `mise self-update` replaces only the mise binary;
    the tool installs under `~/.local/share/mise/installs/` are untouched, so
    the version pins in `~/.config/mise/config.toml` (`go`, `node`, `pnpm`) still
    decide what runs. `mise doctor` reports one benign warning — mise's paths are
    not first in `PATH` because the Pi harness prepends `~/.pi/agent/bin`
    (`rg`, `fd`), which mise does not manage.
- **`PATH` for non-interactive shells — was broken, fixed 2026-09-25.** Until then
  `~/.bash_profile` was a *copy* of `~/.bashrc` opening with the
  `case $- in *i*) ;; *) return;; esac` guard, so every PATH line in it was dead
  code outside a human at a terminal; and because bash prefers
  `~/.bash_profile` for login shells, it shadowed the correct unguarded block in
  `~/.profile`. `env -i HOME=~ bash -lc 'command -v mise'` found nothing — cron,
  `ssh saturn <cmd>`, and other agents all lost the toolchain. `~/.bash_profile`
  is now a thin shim that sources `~/.profile`; the mise toolchain is resolved
  there dynamically via `mise bin-paths` (the real install dirs) and the
  interactive-only aliases, `nuclei_site`/`nuclei_file`, and `mise activate` live
  in `~/.bashrc`. Backups: `~/shell-backup-<ts>/`. Two deliberate choices:
  - **The mise *shims* dir is not on `PATH`.** A shim for a tool with no active
    version aborts with `No version is set for shim: <tool>`, and it shadows
    working system binaries — `pip` was the live example: shimmed it would
    error, unshimmed it is `/usr/bin/pip`. This is the same failure that broke
    `pnpm` before it was registered in `[tools]`, and it produced 18 dead
    Python-era shims here. They are gone: `mise uninstall python@3.12.14`
    removed them itself, and mise only recreates a shim for a tool something
    actually selects — so with no `python` in any `mise.toml`, none comes back.
    `python3` still resolves to `/usr/bin/python3` via a *pass-through* shim
    (mise does not manage it); `toolchain-check` asserts no shim aborts.
  - **A non-login, non-interactive shell still reads no rc file at all**, so
    `ssh saturn 'mise …'` needs absolute paths (`~/.local/bin/mise`) or a
    `BASH_ENV`. That gap is inherent to bash, not to this layout.
  - `/usr/local/go/bin`, which the old `.bash_profile` appended, **does not
    exist** on this host — go comes from mise. The new `.profile` guards on
    `-d`, so the dead entry is gone; the Pi harness `PATH` may still carry it.
- `pnpm` 11.25.0 is mise's own build and it executes fine (no `libatomic.so.1`
  problem, unlike neotokyo) — corepack 0.35.0 is present but unused. It was
  *unregistered* until 2026-09-25: `~/.local/share/mise/installs/pnpm/11.25.0`
  existed while `[tools]` in `~/.config/mise/config.toml` omitted it, so every
  `pnpm` call died with `mise ERROR No version is set for shim: pnpm`. Fixed
  with `mise use -g pnpm@11.25.0`; the `[tools]` table now lists it. Prefer npm
  workspaces for new Node work unless the project already uses pnpm.
- uv provisions its own CPython for project venvs — always use the project
  `.venv` python. All package management via `uv`; never
  `pip install --break-system-packages`.
- Stale venvs: venvs created in other machines/containers have broken symlinks —
  recreate with `uv venv` + `uv pip install` rather than reusing them.
- npm projects in this workspace may hit the install-scripts allowlist
  (e.g. esbuild postinstall) — approve with `npm install-scripts approve <pkg>`.

**Paths.**

| What | Value here |
|---|---|
| `HOME` | `/home/johnn` |
| Workspace | `~/piworkspace` |
| `SKILL_ROOT` | `~/piworkspace/pi-skills` (this file's directory) |
| Global context | `~/.pi/agent/AGENTS.md` → symlink to this file |
| Durable bins | `~/.local/bin` — `cloudflared`, `mise`, session binaries |
| Bin skills | `~/bin/`-style dirs per project; Pi's own bin under `~/.pi/agent/bin` |
| Display | `Xvfb :99` (1366x768x24) for headed Chromium (camofox uses `DISPLAY=:99`) — running as of 2026-09-25, socket `/tmp/.X11-unix/X99` |
| Stale skill copy | `~/piworkspace/opcd-skills/` — a **separate git clone** holding a diverged duplicate of all three skills (`dev-best-practices`, `git-amirulcyber`, `openspec`). Deprecated; `pi-skills` is canonical. Note `git-env.sh`'s legacy credential fallback resolves `../dir-git-amirulcyber/opcd-skills/…` (neotokyo's layout) and therefore finds nothing here — harmless, since the canonical key is present. |

**Docker (via dind socket).**

- Daemon is a dind-sidecar reached at `unix:///var/run/docker.sock` (default
  context; no `DOCKER_HOST` needed — re-verified 2026-09-25: `docker run --rm
  hello-world` OK, `docker compose up` OK). The `DOCKER_HOST=tcp://127.0.0.1:2375`
  note in the neotokyo profile applies to the opencode container, NOT here.
- `docker compose` (plugin form) is the **only** working spelling: the plugin is
  the distro build at `/usr/libexec/docker/cli-plugins/docker-compose` and there
  is no standalone `docker-compose` binary, so a command written as
  `docker-compose …` fails outright. A missing plugin masquerades as a broken
  daemon — check the plugin path before suspecting the socket.
- Container published ports bind on the VM's interfaces (0.0.0.0) — reachable
  from the user's host at `http://10.148.0.3:<port>` **after** opening the port
  in ufw (Docker's NAT/FORWARD chains may bypass ufw INPUT for container ports;
  native processes like `next dev` are pure INPUT and always subject to it).
- Project composes (e.g. `piproject/garudasafev2/garudasafe-app`) run from
  inside via this daemon. The `opencode-infrastructure/docker-compose.yml` stack
  itself stays host-side only (record in `HANDOVER.md`), never `compose up` that
  one from inside.
- Init containers crash on first-boot migration errors: if a service restarts in
  a loop after `docker compose up`, check logs, fix the SQL/config, then
  `docker compose down -v` before retrying (Postgres initdb only runs once per
  volume).

**Git.** Preflight:
`bash ~/piworkspace/pi-skills/git-amirulcyber/scripts/git-env.sh --check`. Flow
per the shared Git section.

**Bug Bounty (standing authorization, 2026-09-20).** Repo
`~/piworkspace/piproject/bugbounty/`; `AUTHORIZATION.md` is the authorization,
its `SKILL.md` is the `pentest-bug-bounty` router. `SKILL_ROOT` for the
engagement (from `20260920-1011-saturn-tools-setup.md`) is
`/home/johnn/piworkspace/piproject/bugbounty` (export it as `BB_ROOT` and
`cd "$BB_ROOT"` first; `BB_ROOT` is **not** set in the environment by default) —
commands reference `$SKILL_ROOT` rather than hardcoding it, and the pentest
toolchain is installed natively: `nuclei`, `subfinder`, `subzy`, `httpx`, `ffuf`
in `~/.local/bin`, and `massdns` in `/usr/local/bin` (not `~/.local/bin`, unlike
the rest). Browser legs for engagements run on this host, pointed at the
neotokyo residential SOCKS leg when a target needs a non-datacenter IP.

The two hosts keep **separate checkouts** of this repo — saturn's is at
`piproject/bugbounty`, neotokyo's at `~/piworkspace/bugbounty`, and only the
saturn path exists on this VM (verified 2026-09-25). Never treat them as one
working tree.

**AI red-team research.** `~/piworkspace/pi-skills/bounty-recon` and the
`ai-security` work; the multi-host tooling rules in this file apply.
