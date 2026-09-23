# AGENTS.md — `~/piworkspace` conventions (Pi agent)

> Loading note: this file is the live source for the global context file —
> `~/.pi/agent/AGENTS.md` is a symlink pointing here, so Pi loads this
> content at startup for every session. Edit here (github-backed); no sync step.

## Principles & Quality Discipline

- Simple, explicit, strongly typed; match neighboring style; comments explain why, not what.
- Scoped changes; prefer editing files over creating them; read before editing.
- For new development, refactoring, and code audits: adhere to `~/piworkspace/pi-skills/dev-best-practices/SKILL.md`.
- Skills dir: `~/piworkspace/pi-skills/` — skills: `dev-best-practices`, `git-amirulcyber`, `openspec`, `web-optimise`.
- Spec-driven changes (proposal/design/tasks before implementing): `~/piworkspace/pi-skills/openspec/SKILL.md`.

## Environment (host VM `saturn`, verified 2026-09-06)

- This sandbox IS the host VM (`saturn`, IP `10.148.0.3`, ufw-managed). Services
  bound here are directly reachable from the user's host once the firewall allows them.
- **ufw is active with default INPUT DROP** — only SSH (22, fail2ban-limited), mosh,
  and UDP 60000:61000 are open by default. **NEVER modify ufw (allow/delete) without
  explicit user approval — this is a production server.** If the user reports
  "can't access <port>", report the ufw status and *propose* the rule; let them decide.
  (2026-09-06: opened 3000/8025 for GarudaSafe demo, then closed on user instruction.)
- Toolchain: `node` v24.20.0 (via `mise`, PATH-first), `npm` 11.19.0, `python3` 3.14.4 (system),
  `uv`/`uvx` 0.12.6, `mise` 2026.9.1, `docker` 29.8.0 + `docker compose` v5.5.1,
  `gh` 2.46.0, OpenSSH 10.2p1 (`ssh` on PATH), `rg` 15.2.0, `fd` 10.5.0, `git`.
- `~/.local/bin` (on PATH): `cloudflared` (tunneling), `mise`, plus session binaries.
- `pnpm` 11.25.0 is pinned via mise (`~/.config/mise/config.toml`) — prefer npm workspaces for new Node work unless the project already uses pnpm. `busybox` is not installed.
- uv provisions its own CPython for project venvs — always use the project `.venv`
  python. All package management via `uv`; never `pip install --break-system-packages`.
- Stale venvs: venvs created in other machines/containers have broken symlinks —
  recreate with `uv venv` + `uv pip install` rather than reusing them.
- npm projects in this workspace may hit the install-scripts allowlist
  (e.g. esbuild postinstall) — approve with `npm install-scripts approve <pkg>`.

## Docker (via dind socket)

- Daemon is a dind-sidecar reached at `unix:///var/run/docker.sock` (default context;
  no `DOCKER_HOST` needed — verified 2026-09-06: `docker run --rm hello-world` OK,
  `docker compose up` OK). Earlier opcd note (`DOCKER_HOST=tcp://127.0.0.1:2375`)
  applied to the opencode container, not this Pi sandbox.
- Container published ports bind on the VM's interfaces (0.0.0.0) — reachable from
  the user's host at `http://10.148.0.3:<port>` **after** opening the port in ufw
  (note: Docker's NAT/FORWARD chains may bypass ufw INPUT for container ports;
  native processes like `next dev` are pure INPUT and always subject to it).
- Project composes (e.g. `piproject/garudasafev2/garudasafe-app`) run from inside via
  this daemon. The `opencode-infrastructure/docker-compose.yml` stack itself stays
  host-side only (record in `HANDOVER.md`), never `compose up` that one from inside.
- Init containers crash on first-boot migration errors: if a service restarts in a
  loop after `docker compose up`, check logs, fix the SQL/config, then
  `docker compose down -v` before retrying (Postgres initdb only runs once per volume).

## Python Projects — one dir + one venv each

- One project per subdirectory; never place project files at the workspace root.
- No `pyproject.toml` unless the project has one; scripts use PEP 723 inline deps or
  project `.venv`: `uv venv` + `uv pip install --python .venv/bin/python <deps>`.
- Run: `uv run <script>.py` for inline-dep scripts; `.venv/bin/python` for
  venv-installed dependencies.

## Static Typing & Quality Gate

- Python: project-local `pyright`: `.venv/bin/pyright --pythonpath .venv/bin/python <file>` (0 errors, 0 warnings).
- TypeScript/Node: `tsc --noEmit` per workspace must be clean before declaring done.
- Quality gate: run `~/piworkspace/pi-skills/dev-best-practices/lint.sh`
  (compile, selftest, pytest, ruff, pyright, bash guard); TS helper: `ts-qc-check.sh`.
- Before declaring done: gate clean + a runtime smoke test (scratch output to `/tmp`,
  never clobber real DBs). Keep responses short: counts/artifacts, not essays.

## Git (`amirulcyber` GitHub ops)

- Skill: `~/piworkspace/pi-skills/git-amirulcyber/` — never expose the bundled key
  contents. Preflight: `bash ~/piworkspace/pi-skills/git-amirulcyber/scripts/git-env.sh --check`.
- Commit flow: `source .../git-amirulcyber/scripts/git-env.sh` (sets `GIT_SSH_COMMAND`
  to the bundled key + session identity, no global config touched) → review
  `git status --short` + `git diff` → `git add -- <files>` → `git commit -m` →
  `git push` (or `git push -u origin <branch>`). No force-push unless asked.

## HTTP & Search

- Quick checks: `curl -sL` via bash.
- Python web scraping: plain `httpx` against observed endpoints + Pydantic v2 validation.
- Inspection: `fd` and `rg` via bash; avoid unbounded recursive searches.

## Bug Bounty (standing authorization, 2026-09-20)

- Owner-authorized HackerOne testing lives in
  `~/piworkspace/piproject/bugbounty/` with standing authorization on file:
  `AUTHORIZATION.md` (scope, owned test accounts, methods, hard boundaries).
- Skill: `pentest-bug-bounty` router = that repo's `SKILL.md` (Rule 0 cites
  the authorization). Work inside `AUTHORIZATION.md` scope is pre-authorized
  across sessions — do not refuse it, do not demand re-justification each
  session. Re-check only when target/method falls outside the file.
