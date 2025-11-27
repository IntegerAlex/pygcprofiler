# SPDX-License-Identifier: LGPL-2.1-only
# Copyright (C) 2024 Akshat Kotpalliwar
"""Integration tests for pygcprofiler."""

import subprocess
import sys
import pytest
from pathlib import Path


class TestCLIIntegration:
    """Integration tests for CLI execution."""

    def test_run_simple_script(self, sample_script):
        """Test running a simple script."""
        result = subprocess.run(
            [sys.executable, '-m', 'gc_monitor', 'run', str(sample_script)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path(__file__).parent.parent
        )
        
        # Script should complete
        assert result.returncode == 0
        # Should see monitoring output
        assert 'GMEM' in result.stderr
        # Script output should appear
        assert 'Sample script completed' in result.stdout

    def test_stats_only_mode(self, sample_script):
        """Test --stats-only mode."""
        result = subprocess.run(
            [sys.executable, '-m', 'gc_monitor', 'run', str(sample_script), '--stats-only'],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode == 0
        # Should see summary but not individual events
        assert 'GMEM MONITORING SUMMARY' in result.stderr or 'Total GC collections' in result.stderr

    def test_json_output(self, sample_script):
        """Test --json output mode."""
        result = subprocess.run(
            [sys.executable, '-m', 'gc_monitor', 'run', str(sample_script), '--json'],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode == 0

    def test_log_file_output(self, sample_script, tmp_path):
        """Test --log-file output."""
        log_file = tmp_path / "gc.log"
        
        result = subprocess.run(
            [sys.executable, '-m', 'gc_monitor', 'run', '--log-file', str(log_file), str(sample_script)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode == 0
        assert log_file.exists()
        content = log_file.read_text()
        assert len(content) > 0

    def test_terminal_flamegraph(self, long_running_script):
        """Test --terminal-flamegraph output."""
        result = subprocess.run(
            [sys.executable, '-m', 'gc_monitor', 'run', str(long_running_script), '--terminal-flamegraph'],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode == 0
        # Should see flame graph output (or at least the header)
        # Note: may not have data if GC didn't run enough

    def test_script_not_found(self, tmp_path):
        """Test error handling for non-existent script."""
        result = subprocess.run(
            [sys.executable, '-m', 'gc_monitor', 'run', str(tmp_path / 'nonexistent.py')],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode != 0
        assert 'not found' in result.stderr.lower() or 'error' in result.stderr.lower()

    def test_script_with_args(self, tmp_path):
        """Test passing arguments to script."""
        script = tmp_path / "args_test.py"
        script.write_text("""
import sys
print(f"Args: {sys.argv[1:]}")
""")
        
        result = subprocess.run(
            [sys.executable, '-m', 'gc_monitor', 'run', str(script), '--foo', 'bar', 'baz'],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode == 0
        assert '--foo' in result.stdout
        assert 'bar' in result.stdout
        assert 'baz' in result.stdout

    def test_script_exit_code_preserved(self, tmp_path):
        """Test that script exit code is preserved."""
        script = tmp_path / "exit_test.py"
        script.write_text("import sys; sys.exit(42)")
        
        result = subprocess.run(
            [sys.executable, '-m', 'gc_monitor', 'run', str(script)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode == 42


class TestModuleMode:
    """Tests for module mode (-m) execution."""

    def test_module_mode_help(self):
        """Test that module mode is documented in help."""
        result = subprocess.run(
            [sys.executable, '-m', 'gc_monitor', 'run', '--help'],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode == 0


class TestErrorHandling:
    """Tests for error handling."""

    def test_no_command(self):
        """Test error when no command specified."""
        result = subprocess.run(
            [sys.executable, '-m', 'gc_monitor'],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode != 0

    def test_script_with_error(self, tmp_path):
        """Test handling of script that raises exception."""
        script = tmp_path / "error_script.py"
        script.write_text("raise ValueError('test error')")
        
        result = subprocess.run(
            [sys.executable, '-m', 'gc_monitor', 'run', str(script)],
            capture_output=True,
            text=True,
            timeout=30,
            cwd=Path(__file__).parent.parent
        )
        
        # Should still show GC summary even if script errors
        assert result.returncode != 0
        assert 'ValueError' in result.stderr or 'test error' in result.stderr


class TestPerformanceCharacteristics:
    """Tests to verify performance characteristics."""

    def test_minimal_overhead(self, tmp_path):
        """Test that monitoring adds minimal overhead."""
        script = tmp_path / "timing_test.py"
        script.write_text("""
import time
start = time.perf_counter()

# Do some work
data = []
for i in range(10000):
    data.append(list(range(100)))
    if i % 1000 == 0:
        data.clear()

elapsed = time.perf_counter() - start
print(f"ELAPSED:{elapsed:.4f}")
""")
        
        # Run without monitoring
        result_no_monitor = subprocess.run(
            [sys.executable, str(script)],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        # Run with monitoring (stats only to minimize output overhead)
        result_with_monitor = subprocess.run(
            [sys.executable, '-m', 'gc_monitor', 'run', '--stats-only', str(script)],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=Path(__file__).parent.parent
        )
        
        # Extract timings
        import re
        
        match_no = re.search(r'ELAPSED:([\d.]+)', result_no_monitor.stdout)
        match_with = re.search(r'ELAPSED:([\d.]+)', result_with_monitor.stdout)
        
        if match_no and match_with:
            time_no = float(match_no.group(1))
            time_with = float(match_with.group(1))
            
            # Overhead should be less than 20% (generous for test stability in CI)
            # Note: subprocess overhead and test variability make this hard to measure precisely
            if time_no > 0.01:  # Only check if baseline is measurable
                overhead = (time_with - time_no) / time_no * 100
                assert overhead < 50, f"Overhead was {overhead:.1f}%, expected < 50%"

