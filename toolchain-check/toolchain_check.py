#!/usr/bin/env python3
"""toolchain_check — post-upgrade / post-rebuild health probe for this workspace.

Stdlib only, so it runs with a bare `python3` and no venv. That is deliberate:
this probe exists to tell you the toolchain is usable, so it must not depend on
the toolchain. A venv-backed checker is circular — venvs are themselves one of
the things that break (see `check_venvs`).

DESIGN — why there are no version floors
-----------------------------------------
The predecessor of this skill (`opencode-system-check`, retired 2026-09-25)
gated on minimum versions. It reported `ok` on a machine that could not run
`pnpm`, could not run `docker compose`, and handed non-interactive shells an
empty `PATH`. Its floors were also duplicated state — a hand-synced table that
silently drifted for a month, and which was necessarily single-host while the
two machines run deliberately different toolchains.

So this gate has no floors. Every check is an **invariant**: a property that,
if false, means something is actually broken. Versions are printed for the
record and never compared. That is why a downgrade is not caught here — it is
also not a failure mode we have ever suffered, whereas a false green is what
the floors caused.

Every check traces to a real incident; see the comment on each.
"""

from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

# ---------------------------------------------------------------------------
# Model
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Result:
    """Outcome of one check.

    `skipped` is distinct from `ok`: a check that could not run (its subject is
    absent on this host) is not a pass, and reporting it as one is how a
    checker starts lying. It is also not a failure — `busybox` is legitimately
    absent on saturn. So: ok / failed / skipped, and only `ok` counts as green.
    """

    name: str
    ok: bool
    detail: str
    skipped: bool = False


@dataclass(frozen=True)
class Tool:
    """A tool this host is expected to provide."""

    name: str
    #: argv prefix that prints a version and exits 0 only if the tool really runs.
    version_argv: tuple[str, ...] = ("--version",)


@dataclass(frozen=True)
class HostProfile:
    """Per-host expectations.

    Kept as data, not as a single shared list: neotokyo has no system Python and
    uses corepack's pnpm, saturn has a system Python and uses mise's. One list
    for both was a bug, not a simplification.
    """

    host_id: str
    #: Tools that must exist AND execute. Presence alone is not enough — an
    #: unregistered mise shim exists on disk and errors when run.
    tools: tuple[Tool, ...]
    #: Extra PATH entries that must contain a real binary.
    required_bins: tuple[str, ...] = ()
    #: Compose invocation. neotokyo has both spellings; saturn has only the
    #: plugin form, so a doc that says `docker-compose` is wrong there.
    compose_argv: tuple[str, ...] = ("docker", "compose")
    #: Directory holding durable, recreate-surviving binaries, or None if the
    #: host keeps them under $HOME instead.
    durable_bin: str | None = None
    #: mise's shim dir. NOT under the workspace — it is on the `.config`/
    #: `.local` bind mounts — so it is named explicitly rather than globbed
    #: relative to the workspace root, which silently finds nothing.
    mise_shims: str | None = "~/.local/share/mise/shims"
    #: Where the workspace actually lives. Never the `/workspace` compat symlink.
    workspace: str = "~/piworkspace"
    #: Throwaway scratch dir, or None when the host declares none. Per-host
    #: because `$SCRATCH` is a container convention: neotokyo's is a tmpfs that
    #: dies on recreate, saturn's is ordinary `/tmp`. A host that declares no
    #: scratch must SKIP, not fail — hardcoding one host's path made this check
    #: report a false failure on the other.
    scratch: str | None = None


NEOTOKYO = HostProfile(
    host_id="neotokyo",
    tools=(
        Tool("mise"),
        Tool("node"),
        Tool("npm"),
        Tool("python3"),
        Tool("pnpm"),
        Tool("uv"),
        Tool("uvx"),
        Tool("gh"),
        Tool("docker"),
        Tool("rg"),
        Tool("fd"),
        Tool("git"),
    ),
    # Both spellings work here: the image CLI and the static tarball carry no
    # compose plugin, so one is symlinked in via $DOCKER_CONFIG. Asserting only
    # the plugin form would pass on neotokyo and be the whole check on saturn.
    compose_argv=("docker", "compose"),
    durable_bin="~/piworkspace/.local/bin",
)

SATURN = HostProfile(
    host_id="saturn",
    tools=(
        Tool("mise"),
        Tool("node"),
        Tool("npm"),
        Tool("python3"),
        Tool("pnpm"),
        Tool("uv"),
        Tool("uvx"),
        Tool("gh"),
        Tool("docker"),
        Tool("rg"),
        Tool("fd"),
        Tool("git"),
    ),
    # No standalone docker-compose binary on this host; the plugin is distro
    # packaged at /usr/libexec/docker/cli-plugins/.
    compose_argv=("docker", "compose"),
    durable_bin="~/.local/bin",
    # Plain /tmp here, not neotokyo's tmpfs: this is a VM, and real artifacts
    # belong in ~/piworkspace regardless. Kept explicit so the check verifies a
    # real directory instead of skipping.
    scratch="/tmp",
)

PROFILES: dict[str, HostProfile] = {"neotokyo": NEOTOKYO, "saturn": SATURN}

#: mise's own failure text for a shim whose tool is not in `[tools]`. Seen on
#: saturn: pnpm was installed under mise/installs but absent from config.toml,
#: so every `pnpm` call died with this. The shim exists, so presence checks pass.
SHIM_ABORT = re.compile(r"No version is set for shim")


# ---------------------------------------------------------------------------
# Probe seam — every side effect goes through here so tests can inject fakes
# ---------------------------------------------------------------------------


class Probe(Protocol):
    """The injected side effects. Tests substitute these; prod uses the real ones."""

    def which(self, name: str) -> str | None: ...
    def run(self, argv: Sequence[str], env: dict[str, str] | None = None) -> tuple[int, str]: ...
    def exists(self, path: Path) -> bool: ...
    def is_symlink(self, path: Path) -> bool: ...
    def readlink(self, path: Path) -> Path: ...
    def writable(self, path: Path) -> bool: ...
    def listdir(self, path: Path) -> list[Path]: ...
    def executable(self, path: Path) -> bool: ...
    def is_file(self, path: Path) -> bool: ...
    def glob(self, pattern: str) -> list[Path]: ...


class RealProbe:
    """Default implementation. Every method is total: it returns a value or a
    benign failure, never raises, because a probe that crashes tells you
    nothing about the box it was meant to inspect."""

    def which(self, name: str) -> str | None:
        return shutil.which(name)

    def run(self, argv: Sequence[str], env: dict[str, str] | None = None) -> tuple[int, str]:
        try:
            # argv is built from literals, never a shell string.
            proc = subprocess.run(
                list(argv),
                capture_output=True,
                text=True,
                timeout=60,
                env=env,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as exc:
            return 127, f"{type(exc).__name__}: {exc}"
        return proc.returncode, (proc.stdout or "") + (proc.stderr or "")

    def exists(self, path: Path) -> bool:
        return path.exists()

    def is_symlink(self, path: Path) -> bool:
        return path.is_symlink()

    def readlink(self, path: Path) -> Path:
        return Path(os.readlink(path))

    def writable(self, path: Path) -> bool:
        return os.access(path, os.W_OK)

    def listdir(self, path: Path) -> list[Path]:
        try:
            return sorted(path.iterdir())
        except OSError:
            return []

    def executable(self, path: Path) -> bool:
        # Routed through the seam rather than called inline: an inline os.access
        # makes the shim check untestable against paths that do not exist, which
        # is the normal case in a unit test. Same for is_file below.
        return os.access(path, os.X_OK)

    def is_file(self, path: Path) -> bool:
        return path.is_file()

    def glob(self, pattern: str) -> list[Path]:
        root = Path(os.path.expanduser("~/piworkspace"))
        return sorted(root.glob(pattern))


# ---------------------------------------------------------------------------
# Checks — each docstring names the incident that motivated it
# ---------------------------------------------------------------------------


def check_marker(profile: HostProfile, probe: Probe) -> Result:
    """The host marker file must exist, and only one of them.

    The whole multi-host design keys off these; with both present the resolver
    would have to guess, and guessing is how the wrong host profile gets applied.
    """
    home = Path(os.path.expanduser("~"))
    present = [h for h in PROFILES if probe.exists(home / "piworkspace" / f"{h}.host")]
    if not present:
        return Result("marker", False, f"no marker file; expected ~/piworkspace/{profile.host_id}.host")
    if len(present) > 1:
        return Result("marker", False, f"ambiguous: markers present for {', '.join(sorted(present))}")
    got = present[0]
    if got != profile.host_id:
        return Result("marker", False, f"marker says {got}, expected {profile.host_id}")
    return Result("marker", True, f"{got}.host")


def check_shell_path(profile: HostProfile, probe: Probe) -> Result:
    """A non-login, non-interactive shell must resolve the toolchain.

    Two separate incidents, one check. On saturn, `~/.bash_profile` was a copy
    of `~/.bashrc` sitting behind the interactive-only `case $- in *i*)` guard,
    and because bash prefers `.bash_profile` for login shells it shadowed the
    correct unguarded block in `~/.profile` — so `env -i HOME=~ bash -lc ...`
    found nothing and cron plus `ssh saturn <cmd>` silently lost mise. On
    neotokyo the tool shell sources no profile at all, so `PATH` had to come
    from `ENV` in the Dockerfile. Probing the caller's own PATH proves
    nothing; the only question that matters is what a fresh shell inherits.
    """
    env = {"HOME": os.path.expanduser("~"), "PATH": os.environ.get("PATH", "")}
    rc, out = probe.run(["bash", "-c", "command -v mise >/dev/null 2>&1 || exit 3"], env)
    if rc == 0:
        return Result("shell_path", True, "mise resolves in a clean non-interactive shell")
    if rc == 3:
        return Result(
            "shell_path",
            False,
            "mise is absent from PATH in a clean non-interactive shell — profile-based "
            "PATH fixes are inert here; set it in the image (ENV) or in ~/.profile",
        )
    return Result("shell_path", False, f"could not probe a clean shell (rc={rc}): {out.strip()[:120]}")


def check_python_interpreter(profile: HostProfile, probe: Probe) -> Result:
    """`python3` must be a real interpreter on disk.

    Two traps in one check. On saturn a mise shim for `python3` sits first on
    PATH but *delegates* rather than providing an interpreter, so `which` lies
    about the provider; neotokyo has no `/usr/bin/python3` at all, so a check
    that assumes a system interpreter is simply wrong there. So: ask the
    interpreter itself via `sys.executable`, and confirm that path exists —
    never infer the provider from PATH order.
    """
    if probe.which("python3") is None:
        return Result("python", False, "python3 not on PATH")
    rc, out = probe.run(["python3", "-c", "import sys; print(sys.executable)"])
    if rc != 0:
        return Result("python", False, f"python3 does not execute (rc={rc}): {out.strip()[:120]}")
    exe = Path(out.strip().splitlines()[-1]) if out.strip() else Path("")
    if not exe.name:
        return Result("python", False, f"python3 printed no executable path (got {out.strip()[:80]!r})")
    if not probe.exists(exe):
        return Result(
            "python",
            False,
            f"python3 reports {exe}, which does not exist — a dangling interpreter "
            "(this is what a venv built on another host looks like)",
        )
    return Result("python", True, f"interpreter {exe}")


def check_tool_runs(profile: HostProfile, probe: Probe) -> Result:
    """Every expected tool must exist *and* execute.

    Presence is not the question. An unregistered mise shim sits on PATH and
    errors on invocation (`No version is set for shim: pnpm`), so a
    which()-only checker reports healthy on a host where the tool is unusable.
    """
    missing: list[str] = []
    broken: list[str] = []
    versions: list[str] = []
    for tool in profile.tools:
        found = probe.which(tool.name)
        if found is None:
            missing.append(tool.name)
            continue
        rc, out = probe.run([tool.name, *tool.version_argv])
        if rc != 0:
            if SHIM_ABORT.search(out):
                broken.append(f"{tool.name} (shim has no active version)")
            else:
                broken.append(f"{tool.name} (rc={rc})")
            continue
        first = out.strip().splitlines()[0] if out.strip() else "?"
        versions.append(f"{tool.name}={first}")
    if missing or broken:
        parts = []
        if missing:
            parts.append(f"absent: {', '.join(missing)}")
        if broken:
            parts.append(f"present but unusable: {', '.join(broken)}")
        return Result("tools", False, "; ".join(parts))
    return Result("tools", True, f"{len(versions)} tools run: " + " ".join(versions))


def check_shim_shadowing(profile: HostProfile, probe: Probe) -> Result:
    """No mise shim on PATH may abort when run.

    A shim for a tool with no active version exits non-zero *and* sits earlier
    on PATH than the working system binary it shadows. On saturn that made
    `pip` error while `/usr/bin/pip` was fine — the same class as pnpm, and it
    is invisible to any `which`-based check.

    The shim dir is named per host, never globbed relative to the workspace: it
    lives on the `.local` bind mount, so a workspace-relative glob finds nothing
    and reports zero. Zero is therefore treated as a FAILURE when mise is
    installed — a check that inspects nothing must not read as a pass, which is
    the same lie this skill exists to stop.
    """
    if profile.mise_shims is None:
        return Result("shims", True, "mise not used on this host", skipped=True)
    if probe.which("mise") is None:
        return Result("shims", True, "mise not installed on this host", skipped=True)
    shim_dir = Path(os.path.expanduser(profile.mise_shims))
    if not probe.exists(shim_dir):
        return Result(
            "shims",
            False,
            f"mise is on PATH but {shim_dir} does not exist — a partial install; every mise "
            "tool will fail to resolve",
        )
    shims = [p for p in probe.listdir(shim_dir) if not probe.is_symlink(p) or probe.exists(p)]
    if not shims:
        return Result(
            "shims",
            False,
            f"{shim_dir} is empty — mise is installed but has no shims, so nothing it manages "
            "is reachable",
        )
    aborting: list[str] = []
    for shim in shims:
        if not probe.is_file(shim) or not probe.executable(shim):
            continue
        rc, out = probe.run([str(shim), "--version"])
        if SHIM_ABORT.search(out):
            aborting.append(shim.name)
    if aborting:
        return Result(
            "shims",
            False,
            f"{len(aborting)} of {len(shims)} mise shim(s) abort and shadow working system "
            f"binaries: {', '.join(sorted(aborting))} — register them in mise's [tools] "
            "or remove the shim",
        )
    return Result("shims", True, f"{len(shims)} mise shim(s), none aborting")


def check_compose(profile: HostProfile, probe: Probe) -> Result:
    """`docker compose` must work, not merely `docker`.

    On neotokyo neither the image CLI nor the static tarball ships a compose
    plugin, so `docker compose` never worked until one was symlinked into
    $DOCKER_CONFIG/cli-plugins — a split where standalone `docker-compose` ran
    and the plugin form failed. On saturn the inverse: the plugin is distro
    packaged and there is no standalone binary, so a command written as
    `docker-compose` fails outright. Checking only `docker --version` passes on
    a host where no compose command can run.
    """
    if probe.which("docker") is None:
        return Result("compose", False, "docker not on PATH")
    rc, out = probe.run([*profile.compose_argv, "version"])
    if rc != 0:
        spelling = " ".join(profile.compose_argv)
        return Result(
            "compose",
            False,
            f"`{spelling} version` failed (rc={rc}) — {out.strip()[:120]}. On neotokyo the "
            "static CLI needs a plugin symlinked into $DOCKER_CONFIG/cli-plugins; on saturn "
            "only the plugin form exists",
        )
    line = out.strip().splitlines()[0] if out.strip() else "?"
    return Result("compose", True, f"`{' '.join(profile.compose_argv)}` works: {line}")


def check_durable_bin(profile: HostProfile, probe: Probe) -> Result:
    """The durable bin dir must exist and hold real binaries.

    This dir is a bind mount, so it is what survives a container recreate. It
    was found empty once after a host-side migration, which is why uv, mise,
    pnpm and docker-compose all vanished at once — a single empty dir looked
    like four unrelated PATH problems.
    """
    if profile.durable_bin is None:
        return Result("durable_bin", True, "not applicable on this host", skipped=True)
    path = Path(os.path.expanduser(profile.durable_bin))
    if not probe.is_symlink(path) and not probe.exists(path):
        return Result(
            "durable_bin",
            False,
            f"{path} is missing — every tool installed there disappears on recreate",
        )
    if not probe.writable(path):
        return Result("durable_bin", False, f"{path} is not writable")
    return Result("durable_bin", True, str(path))


def check_workspace_symlink(profile: HostProfile, probe: Probe) -> Result:
    """The `/workspace` compat symlink must resolve to the real mount.

    It exists so a stale pre-migration path fails visibly instead of writing
    into an unmounted dir. Two things make it dangerous rather than useful: it
    resolving to itself or nowhere, and durable artifacts storing the symlinked
    path. pnpm does exactly that — `.modules.yaml` records the storeDir as a
    literal string, so a stale `/workspace/...` there forces a full
    `node_modules` purge on the next install even though both paths are the
    same directory.
    """
    real = Path(os.path.expanduser(profile.workspace))
    link = Path("/workspace")
    if not probe.exists(link):
        return Result(
            "workspace",
            True,
            "/workspace absent (symlink retired) — nothing resolves through it",
            skipped=True,
        )
    if not probe.is_symlink(link):
        return Result(
            "workspace",
            False,
            "/workspace exists but is not a symlink — a real dir there means the mount is "
            "not wired and writes would go somewhere that does not survive a rebuild",
        )
    target = probe.readlink(link)
    if not target.is_absolute():
        target = (link.parent / target).resolve()
    if not probe.exists(target):
        return Result("workspace", False, f"/workspace -> {target}, which does not exist")
    if target == link:
        return Result("workspace", False, "/workspace points at itself")
    return Result("workspace", True, f"/workspace -> {target} (compat net; prefer {real})")


def check_store_dirs(profile: HostProfile, probe: Probe) -> Result:
    """No `node_modules/.modules.yaml` may record a stale storeDir.

    pnpm resolves its store by walking up to the outermost
    `pnpm-workspace.yaml`, then compares that against the path recorded in
    `.modules.yaml` **as a literal string**. A node_modules installed before the
    workspace moved therefore records the symlinked path, and pnpm then demands
    a destructive full purge on the next install. Observed on garudasafe.
    """
    manifests = probe.glob("*/node_modules/.modules.yaml") + probe.glob("*/*/node_modules/.modules.yaml")
    if not manifests:
        return Result("pnpm_store", True, "no pnpm node_modules present", skipped=True)
    stale: list[str] = []
    for manifest in manifests:
        try:
            recorded = ""
            for line in manifest.read_text(errors="replace").splitlines():
                if line.strip().startswith("storeDir:"):
                    recorded = line.split(":", 1)[1].strip().strip('"')
                    break
        except OSError as exc:  # a specific OSError, not a blind except; a finding, not a crash
            stale.append(f"{manifest.parent}: unreadable ({type(exc).__name__})")
            continue
        if not recorded:
            continue
        # A /workspace-recorded path is the known failure; the mount path is fine.
        if recorded.startswith("/workspace"):
            stale.append(f"{manifest.parent.parent.parent.name}: {recorded}")
    if stale:
        return Result(
            "pnpm_store",
            False,
            "pnpm storeDir recorded via the compat symlink — the next install will demand a "
            f"full purge: {'; '.join(sorted(stale))}. Fix: CI=true pnpm install --frozen-lockfile",
        )
    return Result("pnpm_store", True, f"{len(manifests)} manifest(s), storeDir literal-clean")


def check_venvs(profile: HostProfile, probe: Probe) -> Result:
    """No project `.venv/bin/python` may be a dangling symlink.

    Three venvs were found dead this way: `.venv/bin/python` pointed into a
    deleted uv-managed CPython from the pre-migration container. The activation
    scripts were intact, so the breakage was invisible until something ran —
    and `readlink -f` on a symlink into a deleted dir fails silently in a way
    that looks like a PATH problem.
    """
    pythons = probe.glob("*/.venv/bin/python") + probe.glob("*/*/.venv/bin/python")
    if not pythons:
        return Result("venvs", True, "no project venvs present", skipped=True)
    dead = [str(p) for p in pythons if probe.is_symlink(p) and not probe.exists(p)]
    if dead:
        return Result(
            "venvs",
            False,
            f"{len(dead)} dangling venv interpreter(s) — recreate, do not reuse: "
            f"{', '.join(dead[:3])}. Fix: uv venv --python 3.13 && uv pip install --python .venv/bin/python <deps>",
        )
    return Result("venvs", True, f"{len(pythons)} project venv(s), all interpreters resolve")


def check_scratch(profile: HostProfile, probe: Probe) -> Result:
    """$SCRATCH must be writable, and its durability is reported not required.

    It was root-owned with the image-side chown shadowed by the bind mount, so
    only the host could fix it (EACCES from inside, no sudo to try). The
    durability note matters because the rule was reversed once already: scratch
    is a tmpfs, deliberately, because real artifacts belong in the workspace
    mount. A check that demanded durable scratch would re-break that.
    """
    scratch = os.environ.get("SCRATCH") or profile.scratch
    if not scratch:
        return Result(
            "scratch",
            True,
            f"host {profile.host_id} declares no scratch dir ($SCRATCH unset) — nothing to check",
            skipped=True,
        )
    path = Path(scratch)
    if not probe.exists(path):
        return Result("scratch", False, f"{path} does not exist")
    if not probe.writable(path):
        return Result(
            "scratch",
            False,
            f"{path} is not writable — if it is a bind mount the image-side chown is shadowed "
            "and needs a host-side fix",
        )
    tmpfs = "tmpfs" in Path("/proc/self/mountinfo").read_text(errors="replace") if Path(
        "/proc/self/mountinfo"
    ).exists() else False
    kind = "tmpfs (throwaway, wiped on recreate — correct)" if tmpfs else "durable on disk"
    return Result("scratch", True, f"{path} writable, {kind}")


#: Ordered so the cheapest, most fundamental checks fail first and an agent
#: reading top-down sees the root cause before its symptoms.
CHECKS: tuple[Callable[[HostProfile, Probe], Result], ...] = (
    check_marker,
    check_shell_path,
    check_python_interpreter,
    check_tool_runs,
    check_shim_shadowing,
    check_compose,
    check_durable_bin,
    check_workspace_symlink,
    check_store_dirs,
    check_venvs,
    check_scratch,
)


def run_checks(
    profile: HostProfile,
    probe: Probe | None = None,
    checks: Sequence[Callable[[HostProfile, Probe], Result]] = CHECKS,
) -> list[Result]:
    """Run every check, converting an unexpected raise into a failure.

    A probe that crashes has learned nothing about the box, so a crash must not
    be silently absent from the report — it becomes a red line naming the check.
    """
    active = probe or RealProbe()
    results: list[Result] = []
    for check in checks:
        try:
            results.append(check(profile, active))
        except Exception as exc:  # noqa: BLE001 — a crashing check is a finding, not an abort
            results.append(Result(check.__name__, False, f"check raised {type(exc).__name__}: {exc}"))
    return results


def selftest() -> None:
    """Contract self-test: stdlib only, so it is safe to run from cron or a
    half-broken environment. Asserts the properties a caller depends on."""

    def ok(_p: HostProfile, _probe: Probe) -> Result:
        return Result("ok", True, "fine")

    def bad(_p: HostProfile, _probe: Probe) -> Result:
        return Result("bad", False, "broken")

    def skip(_p: HostProfile, _probe: Probe) -> Result:
        return Result("skip", True, "n/a", skipped=True)

    def boom(_p: HostProfile, _probe: Probe) -> Result:
        raise RuntimeError("probe exploded")

    got = {r.name: r for r in run_checks(NEOTOKYO, RealProbe(), (ok, bad, skip, boom))}
    assert len(got) == 4, "every check must produce exactly one result"
    assert got["ok"].ok and not got["ok"].skipped, "ok must be ok and not skipped"
    assert not got["bad"].ok, "failure must not read as ok"
    assert got["skip"].skipped, "skipped must be distinguishable from ok"
    assert not got["boom"].ok, "a crashing check must fail, not vanish"
    assert "RuntimeError" in got["boom"].detail, "a crash must say what it was"

    # Skipped is not ok: a subject absent on this host must not read as green.
    assert sum(1 for r in got.values() if r.ok and not r.skipped) == 1, "skipped must not count as a pass"
    assert not SHIM_ABORT.match("mise 2026.9.1"), "a real version must not match the shim-abort pattern"
    assert SHIM_ABORT.search("mise ERROR No version is set for shim: pnpm"), "shim abort must match"


def main(argv: Sequence[str]) -> int:
    """CLI entry. Exit 0 only when every check that ran actually passed."""
    if "--selftest" in argv:
        selftest()
        print("# SELFTEST ok")
        return 0

    host = os.environ.get("HOST_ID") or _detect_host()
    profile = PROFILES.get(host)
    if profile is None:
        print(f"# STATUS {json.dumps({'ok': False, 'error': f'unknown host {host!r}'})}")
        print(f"unknown host {host!r}; set HOST_ID to one of {', '.join(PROFILES)}")
        return 2

    results = run_checks(profile)
    passed = sum(1 for r in results if r.ok and not r.skipped)
    failed = [r for r in results if not r.ok]
    skipped = sum(1 for r in results if r.skipped)

    print(f"# HOST {host} · {len(results)} checks · {passed} ok · {len(failed)} failed · {skipped} skipped")
    for r in results:
        mark = "FAIL" if not r.ok else ("SKIP" if r.skipped else "ok  ")
        print(f"  [{mark}] {r.name}: {r.detail}")
    print(
        "# STATUS "
        + json.dumps(
            {
                "ok": not failed,
                "host": host,
                "checks": len(results),
                "passed": passed,
                "failed": len(failed),
                "skipped": skipped,
                "failures": [{"check": r.name, "detail": r.detail} for r in failed],
            }
        )
    )
    return 1 if failed else 0


def _detect_host() -> str:
    """Marker-file resolution, matching the convention in ../AGENTS.md.

    Deliberately does not call `hostname`: the marker is the contract, and a
    hostname happens to be right is not the same as being told.
    """
    home = Path(os.path.expanduser("~"))
    for host_id in PROFILES:
        if (home / "piworkspace" / f"{host_id}.host").exists():
            return host_id
    return os.environ.get("HOSTNAME", "unknown")


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
