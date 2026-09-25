---
name: toolchain-check
description: Post-upgrade / post-rebuild health probe for the agent workspace toolchain. Use after a `just up` container rebuild, a base-image or mise upgrade, a host migration, or whenever a tool "isn't found" / behaves oddly and the cause is not obvious. Gates on invariants (a clean non-interactive shell resolves the toolchain, pnpm actually runs, `docker compose` works, python3 is a real interpreter, no mise shim shadows a system binary, no dangling venv or pnpm storeDir) — never on version numbers, which is why it does not report a healthy broken box.
---

# Toolchain Check

Answers one question: **is this machine's toolchain actually usable right now?**

## Run it

```bash
SKILL_ROOT=~/piworkspace/pi-skills        # per ../AGENTS.md; same string on both hosts
python3 "$SKILL_ROOT/toolchain-check/toolchain_check.py"
```

Stdlib only, so it runs with a bare `python3` and **no venv** — deliberate, since
a venv-backed checker is circular: venvs are themselves one of the things that
break. Exit `0` all-pass, `1` something failed, `2` the host could not be
identified. The last line is machine-readable:

```
# STATUS {"ok": true, "host": "neotokyo", "checks": 11, "passed": 11, "failed": 0, "skipped": 0, "failures": []}
```

Two other entry points:

```bash
python3 toolchain_check.py --selftest   # contract self-test; safe from cron
bash ../dev-best-practices/lint.sh      # full gate: 57 tests, ruff, pyright
```

## When to run it

| Trigger | Why |
|---|---|
| after `just up` / any container rebuild | the image, mounts and `ENV` all change at once |
| after a base-image or `mise self-update` | shims, install dirs and pins move independently |
| after a host migration or a path change | dangling symlinks and stale recorded paths survive it |
| "the tool isn't found" / odd behaviour, cause unclear | this is the case it was built for |

## Why it has no version floors

The skill it replaces (`opencode-system-check`, retired 2026-09-25) gated on
minimum versions. It reported `ok` on a machine that could not run `pnpm`, could
not run `docker compose`, and handed non-interactive shells an empty `PATH`.
Its floors were also duplicated state — a hand-synced table that drifted
silently for a month, and which had to be single-host while the two machines run
deliberately different toolchains.

So there are no floors. Every check is an **invariant**: a property that, if
false, means something is genuinely broken. Versions are printed for the record
and never compared. A downgrade is therefore not caught here — which is fine,
because it is not a failure mode we have ever suffered, whereas a false green is
exactly what the floors caused.

`skipped` is deliberately distinct from `ok`, and only `ok` counts as green. A
check that could not run has not verified anything, and reporting it as a pass
is how a checker starts lying.

## What it checks, and the incident behind each

| Check | Fails when | Incident |
|---|---|---|
| `marker` | no marker file, or both hosts' markers present | resolving the wrong host profile applies the wrong toolchain |
| `shell_path` | a **non-login, non-interactive** shell cannot find mise | saturn's `~/.bash_profile` was a copy of `~/.bashrc` behind the interactive guard, shadowing `~/.profile`; neotokyo's tool shell sources no profile at all, so `PATH` had to come from the image `ENV` |
| `python` | `sys.executable` is not a path that exists | neotokyo has no system Python at all; saturn's mise shim *delegates* rather than providing one, so `which` lies about the provider |
| `tools` | a tool is absent, **or present and unusable** | pnpm was installed under mise but missing from `[tools]`, so every call died while the shim sat happily on `PATH` |
| `shims` | a mise shim aborts, or the shim dir is empty/missing | a shim with no active version also shadows the working system binary — saturn's `pip` vs `/usr/bin/pip` |
| `compose` | `docker compose version` fails | neotokyo shipped no compose plugin at all; saturn has no standalone `docker-compose` binary. `docker --version` passing means nothing |
| `durable_bin` | the recreate-surviving bin dir is missing or unwritable | found empty once, which made uv, mise, pnpm and docker-compose vanish together and looked like four unrelated PATH problems |
| `workspace` | `/workspace` is not a symlink, dangles, or points at itself | the compat symlink is a net for stale paths; a real dir there means the mount is not wired |
| `pnpm_store` | a `.modules.yaml` records `storeDir` via the compat symlink | pnpm compares it as a **literal string**, so a stale path forces a destructive full `node_modules` purge on the next install |
| `venvs` | a project `.venv/bin/python` is a dangling symlink | three were dead after the migration, with intact activation scripts — invisible until something ran |
| `scratch` | `$SCRATCH` is missing or unwritable | root-owned with the image-side `chown` shadowed by the bind mount: EACCES from inside, no sudo to try |

Ordered cheapest-and-most-fundamental first, so a top-down read shows the root
cause before its symptoms.

## Extending it

Add a check as a function taking `(profile, probe) -> Result`, append it to
`CHECKS`, and **route every side effect through `Probe`**. That rule is not
theoretical: three checks were initially written with inline `os.access`,
`Path.is_file()` and `read_text()`, which made them untestable against paths
that do not exist on the real disk — so the suite "passed" while the checks
silently inspected nothing. `check_shim_shadowing` shipped with exactly that
bug, globbing relative to the workspace and reporting `0 shim(s), none
aborting` when 22 existed.

Two guards keep that class from returning:

- an **empty** subject is a failure, never a pass — if mise is installed and the
  shim dir is empty, that is a broken install, not a pass
- every check needs at least one test that goes **red**; the predecessor only
  ever exercised the paths that pass

For a new host, add a `HostProfile` to `PROFILES` — per-host expectations are
the point, not boilerplate, since the two machines differ on exactly the
properties worth checking (system Python present or not, `pnpm` from corepack or
mise, compose plugin on both spellings or one).

## Rules (from `../dev-best-practices/SKILL.md`)

- `toolchain_check.py` stays **stdlib only** so it can run from cron or a
  half-broken environment, and so a project venv is never a dependency.
- No check may raise out of `run_checks`; a crash is caught and reported as a
  red line, because a probe that crashed has learned nothing about the box.
- Test fakes are built by a factory per test — never shared mutable state, and
  every side effect is injected, so no test damages the real machine.
- The suite points `HOME` at a fake dir, so it never depends on the host's
  layout. The live tests hand the real `HOME` back, because mise shims resolve
  their installs through it.
