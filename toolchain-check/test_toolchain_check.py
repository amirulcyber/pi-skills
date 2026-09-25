"""Regression suite for toolchain_check.

Two rules govern this file, both carried over from the checker it replaces and
hardened:

1. **Every check is tested through an injected `FakeProbe`, never by breaking
   the real machine.** A test suite that damages the box it runs on is a
   different kind of liability. The one exception is `test_live_*` below, which
   asserts presence and nothing else.

2. **Every failure path is covered, not just the happy one.** The predecessor
   reported `ok` on a machine where pnpm, `docker compose` and the non-
   interactive PATH were all broken, because it only ever exercised the paths
   that pass. Each check below has at least one test that must go red.

Tests are built by factory functions per test — never shared mutable state, and
no module-level fake that a test can mutate out from under another.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

import toolchain_check as tc

#: Captured at import, before any test monkeypatches HOME, for the CLI tests
#: that must resolve the real marker file.
REAL_HOME = os.path.expanduser("~")

#: Every check resolves paths through `expanduser("~")`, so the suite points
#: HOME here and is therefore hermetic — it never depends on this machine's
#: layout, and never touches its real files.
FAKE_HOME = Path("/home/tester")


@pytest.fixture(autouse=True)
def _isolate_home(monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("HOME", str(FAKE_HOME))
    return FAKE_HOME


# ---------------------------------------------------------------------------
# Fakes — one factory per test so no state is shared
# ---------------------------------------------------------------------------


class FakeProbe:
    """Records calls and returns scripted answers. Every method is total."""

    def __init__(
        self,
        *,
        which: dict[str, str | None] | None = None,
        run: dict[tuple[str, ...], tuple[int, str]] | None = None,
        exists: set[Path] | None = None,
        symlinks: dict[Path, Path] | None = None,
        writable: set[Path] | None = None,
        executable: set[Path] | None = None,
        listdir: dict[Path, list[Path]] | None = None,
        glob: dict[str, list[Path]] | None = None,
    ) -> None:
        self._which = which or {}
        self._run = run or {}
        self._exists = exists or set()
        self._symlinks = symlinks or {}
        self._writable = writable or set()
        self._executable = executable or set()
        self._listdir = listdir or {}
        self._glob = glob or {}

    def which(self, name: str) -> str | None:
        return self._which.get(name)

    def run(self, argv: Sequence[str], env: dict[str, str] | None = None) -> tuple[int, str]:
        return self._run.get(tuple(argv), (0, ""))

    def exists(self, path: Path) -> bool:
        # Deliberately does NOT treat "is a registered symlink" as existing: a
        # dangling symlink is exactly the condition check_venvs and
        # check_workspace_symlink exist to catch, so the fake must be able to
        # express one.
        return path in self._exists

    def is_symlink(self, path: Path) -> bool:
        return path in self._symlinks

    def readlink(self, path: Path) -> Path:
        return self._symlinks[path]

    def writable(self, path: Path) -> bool:
        return path in self._writable

    def listdir(self, path: Path) -> list[Path]:
        return self._listdir.get(path, [])

    def executable(self, path: Path) -> bool:
        return path in self._executable

    def is_file(self, path: Path) -> bool:
        return path in self._executable

    def glob(self, pattern: str) -> list[Path]:
        return self._glob.get(pattern, [])


def _healthy_probe(
    *,
    which: dict[str, str | None] | None = None,
    run: dict[tuple[str, ...], tuple[int, str]] | None = None,
    exists: set[Path] | None = None,
    symlinks: dict[Path, Path] | None = None,
    writable: set[Path] | None = None,
    executable: set[Path] | None = None,
    listdir: dict[Path, list[Path]] | None = None,
    glob: dict[str, list[Path]] | None = None,
) -> FakeProbe:
    """A probe on which every check passes, so each test can break exactly one
    thing and be certain the failure it sees is the one it caused.

    Overrides are merged last, so a test that needs a different default just
    names it instead of mutating the healthy state afterwards.
    """
    home = FAKE_HOME
    shims = home / ".local/share/mise/shims"
    shim_files = [shims / "mise", shims / "node"]

    answers: dict[tuple[str, ...], tuple[int, str]] = {
        ("bash", "-c", "command -v mise >/dev/null 2>&1 || exit 3"): (0, ""),
        ("python3", "-c", "import sys; print(sys.executable)"): (0, "/usr/bin/python3\n"),
        ("docker", "compose", "version"): (0, "Docker Compose version v5.5.1"),
    }
    for tool in tc.NEOTOKYO.tools:
        answers[(tool.name, *tool.version_argv)] = (0, f"{tool.name} 1.2.3")
    for shim in shim_files:
        answers[(str(shim), "--version")] = (0, "1.2.3")
    answers.update(run or {})

    return FakeProbe(
        which=which or {t.name: f"/usr/bin/{t.name}" for t in tc.NEOTOKYO.tools},
        run=answers,
        exists=exists
        or {
            home / "piworkspace/neotokyo.host",
            Path("/usr/bin/python3"),
            home / "piworkspace/.local/bin",
            home / "piworkspace",
            shims,
            *shim_files,
        },
        symlinks=symlinks or {},
        writable=writable or {home / "piworkspace/.local/bin"},
        executable=executable or set(shim_files),
        listdir=listdir or {shims: shim_files},
        glob=glob or {},
    )


# ---------------------------------------------------------------------------
# The central contract: skipped is not ok
# ---------------------------------------------------------------------------


def test_selftest_contract() -> None:
    assert tc.selftest() is None


def test_skipped_is_not_counted_as_a_pass() -> None:
    """The retired checker reported `ok` on a broken box. The guard against that
    is that a check which could not run never counts as green."""
    skipped = tc.Result("s", True, "n/a", skipped=True)
    assert skipped.ok and skipped.skipped
    assert not (skipped.ok and not skipped.skipped), "skipped must be distinguishable from ok"


def test_run_checks_converts_a_crash_into_a_failure() -> None:
    """A probe that raises has learned nothing, so it must appear as red rather
    than silently vanish from the report."""

    def exploding(_p: tc.HostProfile, _probe: tc.Probe) -> tc.Result:
        raise RuntimeError("kaboom")

    results = tc.run_checks(tc.NEOTOKYO, _healthy_probe(), (exploding,))
    assert len(results) == 1
    assert not results[0].ok
    assert "RuntimeError" in results[0].detail


# ---------------------------------------------------------------------------
# check_marker
# ---------------------------------------------------------------------------


def test_marker_absent_fails_loud() -> None:
    probe = _healthy_probe()
    probe._exists.clear()
    got = tc.check_marker(tc.NEOTOKYO, probe)
    assert not got.ok
    assert "no marker" in got.detail


def test_marker_ambiguous_fails() -> None:
    home = Path("/home/tester")
    probe = _healthy_probe()
    probe._exists.add(home / "piworkspace/saturn.host")
    got = tc.check_marker(tc.NEOTOKYO, probe)
    assert not got.ok
    assert "ambiguous" in got.detail


def test_marker_mismatch_fails() -> None:
    """A saturn marker while running the neotokyo profile means the wrong
    profile would be applied — the exact failure the marker exists to prevent."""
    probe = _healthy_probe()
    probe._exists.discard(FAKE_HOME / "piworkspace/neotokyo.host")
    probe._exists.add(FAKE_HOME / "piworkspace/saturn.host")
    got = tc.check_marker(tc.NEOTOKYO, probe)
    assert not got.ok
    assert "marker says saturn" in got.detail


# ---------------------------------------------------------------------------
# check_shell_path — the incident that motivated the whole skill
# ---------------------------------------------------------------------------


def test_shell_path_ok_when_mise_resolves() -> None:
    assert tc.check_shell_path(tc.NEOTOKYO, _healthy_probe()).ok


def test_shell_path_fails_when_a_clean_shell_has_no_mise() -> None:
    """saturn's `.bash_profile` shadowed `.profile`, so cron and `ssh saturn
    <cmd>` found nothing while an interactive shell was fine."""
    probe = _healthy_probe()
    probe._run[("bash", "-c", "command -v mise >/dev/null 2>&1 || exit 3")] = (3, "")
    got = tc.check_shell_path(tc.NEOTOKYO, probe)
    assert not got.ok
    assert "non-interactive" in got.detail


def test_shell_path_fails_when_bash_itself_is_broken() -> None:
    probe = _healthy_probe()
    probe._run[("bash", "-c", "command -v mise >/dev/null 2>&1 || exit 3")] = (127, "not found")
    got = tc.check_shell_path(tc.NEOTOKYO, probe)
    assert not got.ok
    assert "could not probe" in got.detail


# ---------------------------------------------------------------------------
# check_python_interpreter — the dangling-symlink class
# ---------------------------------------------------------------------------


def test_python_reports_its_own_executable() -> None:
    assert tc.check_python_interpreter(tc.NEOTOKYO, _healthy_probe()).ok


def test_python_fails_when_sys_executable_does_not_exist() -> None:
    """A venv built on another host points at a deleted CPython. `which` still
    succeeds, so only asking the interpreter catches it."""
    probe = _healthy_probe()
    probe._run[("python3", "-c", "import sys; print(sys.executable)")] = (
        0,
        "/home/appuser/.local/share/uv/python/cpython-3.13/bin/python3\n",
    )
    got = tc.check_python_interpreter(tc.NEOTOKYO, probe)
    assert not got.ok
    assert "does not exist" in got.detail


def test_python_fails_when_it_does_not_execute() -> None:
    probe = _healthy_probe()
    probe._run[("python3", "-c", "import sys; print(sys.executable)")] = (1, "boom")
    assert not tc.check_python_interpreter(tc.NEOTOKYO, probe).ok


def test_python_fails_when_it_prints_nothing() -> None:
    probe = _healthy_probe()
    probe._run[("python3", "-c", "import sys; print(sys.executable)")] = (0, "")
    assert not tc.check_python_interpreter(tc.NEOTOKYO, probe).ok


# ---------------------------------------------------------------------------
# check_tool_runs — presence is not the question
# ---------------------------------------------------------------------------


def test_tools_ok_when_all_execute() -> None:
    assert tc.check_tool_runs(tc.NEOTOKYO, _healthy_probe()).ok


def test_tools_reports_absent_separately_from_broken() -> None:
    probe = _healthy_probe()
    probe._which.pop("rg")
    probe._run[("fd", "--version")] = (1, "")
    got = tc.check_tool_runs(tc.NEOTOKYO, probe)
    assert not got.ok
    assert "absent: rg" in got.detail
    assert "present but unusable: fd" in got.detail


def test_tools_flags_a_shim_with_no_active_version() -> None:
    """pnpm on saturn: the shim existed on PATH, so presence passed, but every
    invocation died. This is the check the retired version linter could not do."""
    probe = _healthy_probe()
    probe._run[("pnpm", "--version")] = (1, "mise ERROR No version is set for shim: pnpm")
    got = tc.check_tool_runs(tc.NEOTOKYO, probe)
    assert not got.ok
    assert "shim has no active version" in got.detail


# ---------------------------------------------------------------------------
# check_shim_shadowing — including the bug this skill shipped with
# ---------------------------------------------------------------------------


def test_shims_ok_when_none_abort() -> None:
    assert tc.check_shim_shadowing(tc.NEOTOKYO, _healthy_probe()).ok


def test_shims_flag_an_aborting_shadow() -> None:
    shim_dir = FAKE_HOME / ".local/share/mise/shims"
    pip_shim = shim_dir / "pip"
    probe = _healthy_probe(listdir={shim_dir: [shim_dir / "mise", pip_shim]})
    probe._listdir[shim_dir] = [shim_dir / "mise", pip_shim]
    probe._executable.add(pip_shim)
    probe._run[(str(pip_shim), "--version")] = (1, "mise ERROR No version is set for shim: pip")
    got = tc.check_shim_shadowing(tc.NEOTOKYO, probe)
    assert not got.ok
    assert "pip" in got.detail
    assert "shadow" in got.detail


def test_empty_shim_dir_fails_rather_than_reporting_zero_as_a_pass() -> None:
    """Regression guard for the bug this checker shipped with: a
    workspace-relative glob found no shims and printed `0 shim(s), none
    aborting`, which reads as a pass. Inspecting nothing must be red."""
    shim_dir = FAKE_HOME / ".local/share/mise/shims"
    probe = _healthy_probe(listdir={shim_dir: []})
    probe._listdir[shim_dir] = []
    got = tc.check_shim_shadowing(tc.NEOTOKYO, probe)
    assert not got.ok
    assert "empty" in got.detail


def test_missing_shim_dir_fails_when_mise_is_installed() -> None:
    shim_dir = FAKE_HOME / ".local/share/mise/shims"
    probe = _healthy_probe()
    probe._exists.discard(shim_dir)
    got = tc.check_shim_shadowing(tc.NEOTOKYO, probe)
    assert not got.ok
    assert "partial install" in got.detail


def test_shims_skipped_when_mise_absent() -> None:
    probe = _healthy_probe()
    probe._which.pop("mise")
    got = tc.check_shim_shadowing(tc.NEOTOKYO, probe)
    assert got.ok and got.skipped


# ---------------------------------------------------------------------------
# check_compose — neotokyo had neither form, saturn has only the plugin form
# ---------------------------------------------------------------------------


def test_compose_ok() -> None:
    assert tc.check_compose(tc.NEOTOKYO, _healthy_probe()).ok


def test_compose_fails_when_only_docker_itself_works() -> None:
    """The split that cost a session: `docker --version` fine, `docker compose`
    broken because no plugin was installed."""
    probe = _healthy_probe()
    probe._run[("docker", "compose", "version")] = (1, "unknown command")
    got = tc.check_compose(tc.NEOTOKYO, probe)
    assert not got.ok
    assert "DOCKER_CONFIG" in got.detail


def test_compose_fails_when_docker_absent() -> None:
    probe = _healthy_probe()
    probe._which.pop("docker")
    assert not tc.check_compose(tc.NEOTOKYO, probe).ok


def test_saturn_uses_the_plugin_spelling_only() -> None:
    """saturn has no standalone docker-compose binary, so a doc or script
    written as `docker-compose` fails there. The profile must not ask for it."""
    assert tc.SATURN.compose_argv == ("docker", "compose")


# ---------------------------------------------------------------------------
# check_durable_bin
# ---------------------------------------------------------------------------


def test_durable_bin_ok() -> None:
    assert tc.check_durable_bin(tc.NEOTOKYO, _healthy_probe()).ok


def test_durable_bin_missing_fails() -> None:
    """Found empty once, which made uv, mise, pnpm and docker-compose all vanish
    at once and looked like four unrelated PATH problems."""
    probe = _healthy_probe()
    probe._exists.discard(FAKE_HOME / "piworkspace/.local/bin")
    got = tc.check_durable_bin(tc.NEOTOKYO, probe)
    assert not got.ok
    assert "disappears on recreate" in got.detail


def test_durable_bin_not_writable_fails() -> None:
    probe = _healthy_probe()
    probe._writable.clear()
    got = tc.check_durable_bin(tc.NEOTOKYO, probe)
    assert not got.ok
    assert "not writable" in got.detail


# ---------------------------------------------------------------------------
# check_workspace_symlink
# ---------------------------------------------------------------------------


def test_workspace_ok_when_symlink_resolves() -> None:
    probe = _healthy_probe()
    probe._symlinks[Path("/workspace")] = FAKE_HOME / "piworkspace"
    probe._exists.add(Path("/workspace"))
    assert tc.check_workspace_symlink(tc.NEOTOKYO, probe).ok


def test_workspace_absent_is_skipped_not_failed() -> None:
    """Retiring the symlink is the goal state, not a fault."""
    probe = _healthy_probe()
    got = tc.check_workspace_symlink(tc.NEOTOKYO, probe)
    assert got.ok and got.skipped


def test_workspace_real_dir_fails() -> None:
    """A real dir at /workspace means the mount is not wired; writes would go
    somewhere that does not survive a rebuild."""
    probe = _healthy_probe()
    probe._exists.add(Path("/workspace"))
    got = tc.check_workspace_symlink(tc.NEOTOKYO, probe)
    assert not got.ok
    assert "not a symlink" in got.detail


def test_workspace_dangling_fails() -> None:
    probe = _healthy_probe()
    probe._symlinks[Path("/workspace")] = FAKE_HOME / "gone"
    probe._exists.add(Path("/workspace"))
    assert not tc.check_workspace_symlink(tc.NEOTOKYO, probe).ok


# ---------------------------------------------------------------------------
# check_store_dirs — the literal-string comparison
# ---------------------------------------------------------------------------


def _store_probe(tmp_path: Path, recorded: str) -> FakeProbe:
    manifest = tmp_path / "node_modules/.modules.yaml"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(f'hoistedDependencies: {{}}\nstoreDir: {recorded}\n')
    return _healthy_probe(
        glob={"*/node_modules/.modules.yaml": [manifest], "*/*/node_modules/.modules.yaml": []}
    )


def test_store_dir_clean(tmp_path: Path) -> None:
    probe = _store_probe(tmp_path, "/home/tester/piworkspace/.pnpm-store/v11")
    assert tc.check_store_dirs(tc.NEOTOKYO, probe).ok


def test_store_dir_via_compat_symlink_fails(tmp_path: Path) -> None:
    """pnpm compares storeDir as a literal string, so a stale /workspace path
    forces a destructive full node_modules purge on the next install."""
    probe = _store_probe(tmp_path, "/workspace/.pnpm-store/v11")
    got = tc.check_store_dirs(tc.NEOTOKYO, probe)
    assert not got.ok
    assert "purge" in got.detail


def test_store_dir_absent_is_skipped() -> None:
    got = tc.check_store_dirs(tc.NEOTOKYO, _healthy_probe())
    assert got.ok and got.skipped


# ---------------------------------------------------------------------------
# check_venvs
# ---------------------------------------------------------------------------


def test_venvs_ok() -> None:
    live = FAKE_HOME / "proj/.venv/bin/python"
    probe = _healthy_probe(glob={"*/.venv/bin/python": [live], "*/*/.venv/bin/python": []})
    probe._exists.add(live)
    assert tc.check_venvs(tc.NEOTOKYO, probe).ok


def test_dangling_venv_interpreter_fails() -> None:
    """Three of these were found after the workspace migration, with intact
    activation scripts — so nothing looked wrong until something ran."""
    dead = FAKE_HOME / "proj/.venv/bin/python"
    probe = _healthy_probe(glob={"*/.venv/bin/python": [dead], "*/*/.venv/bin/python": []})
    probe._symlinks[dead] = Path("/home/appuser/.local/share/uv/python/cpython-3.13/bin/python3")
    got = tc.check_venvs(tc.NEOTOKYO, probe)
    assert not got.ok
    assert "uv venv --python 3.13" in got.detail


def test_no_venvs_is_skipped() -> None:
    got = tc.check_venvs(tc.NEOTOKYO, _healthy_probe())
    assert got.ok and got.skipped


# ---------------------------------------------------------------------------
# check_scratch
# ---------------------------------------------------------------------------


def test_scratch_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCRATCH", "/tmp/scratch-probe")
    probe = _healthy_probe(
        exists={Path("/tmp/scratch-probe")},
        writable={Path("/tmp/scratch-probe")},
    )
    assert tc.check_scratch(tc.NEOTOKYO, probe).ok


def test_scratch_missing_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SCRATCH", "/tmp/definitely-not-here")
    got = tc.check_scratch(tc.NEOTOKYO, _healthy_probe())
    assert not got.ok
    assert "does not exist" in got.detail


def test_scratch_unwritable_fails(monkeypatch: pytest.MonkeyPatch) -> None:
    """Root-owned with the image-side chown shadowed by the bind mount: EACCES
    from inside the container with no sudo to try."""
    monkeypatch.setenv("SCRATCH", "/tmp/scratch-probe")
    probe = _healthy_probe(exists={Path("/tmp/scratch-probe")}, writable=set())
    got = tc.check_scratch(tc.NEOTOKYO, probe)
    assert not got.ok
    assert "not writable" in got.detail


# ---------------------------------------------------------------------------
# CLI contract
# ---------------------------------------------------------------------------


def _cli(*args: str, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    # Fixed argv, no shell.
    return subprocess.run(
        [sys.executable, str(Path(__file__).with_name("toolchain_check.py")), *args],
        capture_output=True,
        text=True,
        check=False,
        # HOME is handed back explicitly: the autouse fixture points it at a fake
        # dir, and the CLI resolves the host from the real marker file.
        env={**os.environ, "HOME": REAL_HOME, **(env or {})},
    )


def test_cli_emits_machine_readable_status() -> None:
    proc = _cli()
    assert proc.returncode in (0, 1), "must gate, never crash"
    line = next(ln for ln in proc.stdout.splitlines() if ln.startswith("# STATUS "))
    payload = json.loads(line.removeprefix("# STATUS "))
    assert set(payload) >= {"ok", "host", "checks", "passed", "failed", "failures"}


def test_cli_unknown_host_exits_two() -> None:
    proc = _cli(env={"HOST_ID": "atlantis"})
    assert proc.returncode == 2
    assert "unknown host" in proc.stdout


def test_cli_selftest_exits_zero() -> None:
    assert _cli("--selftest").returncode == 0


# ---------------------------------------------------------------------------
# Live presence tests — assert only that things exist, never a version
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("tool", [t.name for t in tc.NEOTOKYO.tools], ids=lambda n: n)
def test_live_tool_runs(tool: str, monkeypatch: pytest.MonkeyPatch) -> None:
    """Real HOME: mise shims resolve their installs through $HOME, so the
    autouse fake would break every mise-managed tool."""
    import shutil

    monkeypatch.setenv("HOME", REAL_HOME)
    if shutil.which(tool) is None:
        pytest.skip(f"{tool} is absent on this host by design")
    assert tc.RealProbe().run([tool, "--version"])[0] == 0


def test_live_selftest() -> None:
    assert tc.selftest() is None


# ---------------------------------------------------------------------------
# The property that makes cron-safety possible
# ---------------------------------------------------------------------------


def test_checker_imports_stdlib_only() -> None:
    """`toolchain_check.py` must stay importable with a bare `python3`.

    The whole point of a stdlib-only probe is that it runs where the toolchain
    is already broken — a venv or a third-party import is exactly the kind of
    thing that is missing at that moment. Nothing else stops a future
    convenience import from quietly removing that guarantee, so assert it.
    """
    import ast

    allowed = set(sys.stdlib_module_names) | {"toolchain_check"}
    imported: set[str] = set()
    tree = ast.parse((Path(__file__).with_name("toolchain_check.py")).read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            imported.add(node.module.split(".")[0])
    assert not (imported - allowed), f"non-stdlib imports would break cron-safety: {imported - allowed}"
