import os
import shutil
import sys
import subprocess
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
GC_UTIL = PROJECT_ROOT / "gc-util.py"
TEST_SCRIPT = PROJECT_ROOT / "test.py"
TEST_MODULE = "pygctest.main"


@pytest.mark.parametrize(
    "extra_flags",
    [
        pytest.param([], id="no_flags"),
        pytest.param(["--json"], id="json"),
        pytest.param(["--stats-only"], id="stats_only"),
        pytest.param(["--json", "--stats-only"], id="json_stats"),
        pytest.param(["--dump-objects"], id="dump_objects"),
        pytest.param(["--dump-garbage"], id="dump_garbage"),
        pytest.param(["--log-file", "tmp-gc.log"], id="log_file"),
        pytest.param(["--alert-threshold-ms", "5"], id="alert_threshold"),
        pytest.param(["--flamegraph-file", "tmp-flame.txt"], id="flamegraph_file"),
        pytest.param(
            ["--terminal-flamegraph", "--terminal-flamegraph-width", "100"],
            id="terminal_flamegraph_width",
        ),
        pytest.param(
            ["--terminal-flamegraph", "--terminal-flamegraph-color"],
            id="terminal_flamegraph_color",
        ),
        pytest.param(
            ["--duration-buckets", "1,10,100"],
            id="duration_buckets",
        ),
        pytest.param(
            ["--prompt"],
            id="prompt",
        ),
        pytest.param(
            [
                "--json",
                "--stats-only",
                "--dump-objects",
                "--dump-garbage",
                "--alert-threshold-ms",
                "5",
                "--duration-buckets",
                "1,5,20,50,100",
            ],
            id="heavy_combo",
        ),
    ],
)
def test_gc_util_run_flags(extra_flags, tmp_path):
    """Smoke-test gc-util.py run with various flag combinations.

    These tests ensure that the CLI wiring and monitoring pipeline
    accept the flags and exit successfully when running a simple script.
    """
    env = os.environ.copy()
    # Ensure any log / flamegraph files go into a temp directory when relevant
    cmd = [sys.executable, str(GC_UTIL), "run"]

    # Redirect output files into tmp_path when relevant, and remember them for assertions.
    flags: list[str] = []
    output_files: list[Path] = []
    it = iter(extra_flags)
    for item in it:
        if item in {"--log-file", "--flamegraph-file"}:
            # Replace file argument with a path under tmp_path
            try:
                _ = next(it)
            except StopIteration:
                break
            filename = "gc.log" if item == "--log-file" else "flame.txt"
            file_path = tmp_path / filename
            output_files.append(file_path)
            flags.extend([item, str(file_path)])
        else:
            flags.append(item)

    cmd.extend(flags)
    cmd.append(str(TEST_SCRIPT))

    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )

    assert result.returncode == 0, f"Command failed: {cmd}\nstderr:\n{result.stderr}"
    # Basic sanity check: banner should be present for run command
    assert "pygcprofiler - See Python's garbage collector in action without getting in its way." in result.stderr
    # No unexpected tracebacks or generic "Error:" lines on successful runs.
    assert "Traceback (most recent call last)" not in result.stderr
    assert "Error:" not in result.stderr
    # If we asked for output files, they should have been created (and be non-empty where reasonable).
    for path in output_files:
        assert path.exists(), f"Expected output file was not created: {path}"
        # Allow empty flamegraph files in degenerate cases, but log files should have some content.
        if path.name.endswith(".log"):
            assert path.read_text() != ""


def _run_gc_util(args: list[str]) -> subprocess.CompletedProcess[str]:
    """Helper to run gc-util.py and capture output."""
    env = os.environ.copy()
    cmd = [sys.executable, str(GC_UTIL)] + args
    return subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )


def test_gc_util_missing_script_exits_with_error():
    """gc-util.py run without an existing script should exit with code 1 and a clear error."""
    result = _run_gc_util(["run", "does_not_exist.py"])
    assert result.returncode == 1
    assert "Error: Script file not found: does_not_exist.py" in result.stderr


def test_gc_util_misplaced_flags_error():
    """Flags after the script should trigger the flag-ordering error."""
    result = _run_gc_util(["run", str(TEST_SCRIPT), "--json"])
    assert result.returncode == 2
    assert "Error: gc-util/pygcprofiler flags must appear before the script path." in result.stderr


def test_pygcprofiler_module_mode_with_pygctest():
    """Verify that module-mode (-m) works when using the pygcprofiler CLI (via gc_monitor.__main__)."""
    env = os.environ.copy()
    # Ensure both src/ and pygctest/ are in PYTHONPATH so modules are importable
    src_path = str(PROJECT_ROOT / "src")
    pygctest_path = str(PROJECT_ROOT)
    env["PYTHONPATH"] = os.pathsep.join([src_path, pygctest_path, env.get("PYTHONPATH", "")])

    # Test module mode without requiring -- separator
    # The CLI should handle -m automatically
    cmd = [
        sys.executable,
        "-m",
        "gc_monitor",
        "run",
        "-m",
        TEST_MODULE,
    ]

    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,  # Prevent hanging
    )

    assert result.returncode == 0, f"Module-mode run failed: {cmd}\nstderr:\n{result.stderr}\nstdout:\n{result.stdout}"
    assert "pygcprofiler - See Python's garbage collector in action without getting in its way." in result.stderr
    assert "Traceback (most recent call last)" not in result.stderr
    # Verify the module actually ran
    assert "Hello from pygctest!" in result.stdout or "Hello from pygctest!" in result.stderr


def test_pygcprofiler_module_mode_with_live_flag():
    """Verify that --live flag works with module-mode (-m)."""
    env = os.environ.copy()
    # Ensure both src/ and pygctest/ are in PYTHONPATH so modules are importable
    src_path = str(PROJECT_ROOT / "src")
    pygctest_path = str(PROJECT_ROOT)
    env["PYTHONPATH"] = os.pathsep.join([src_path, pygctest_path, env.get("PYTHONPATH", "")])

    # Test --live with module mode: pygcprofiler run --live -m module
    cmd = [
        sys.executable,
        "-m",
        "gc_monitor",
        "run",
        "--live",
        "-m",
        TEST_MODULE,
    ]

    result = subprocess.run(
        cmd,
        cwd=str(PROJECT_ROOT),
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        timeout=30,  # Prevent hanging (dashboard auto-start might take a moment)
    )

    assert result.returncode == 0, f"Module-mode with --live failed: {cmd}\nstderr:\n{result.stderr}\nstdout:\n{result.stdout}"
    assert "pygcprofiler - See Python's garbage collector in action without getting in its way." in result.stderr
    assert "Traceback (most recent call last)" not in result.stderr
    # Verify live monitoring was enabled (dashboard auto-starts)
    assert "GMEM Dashboard auto-started" in result.stderr or "live monitoring" in result.stderr.lower()
    # Verify the module actually ran
    assert "Hello from pygctest!" in result.stdout or "Hello from pygctest!" in result.stderr


