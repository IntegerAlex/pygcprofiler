# SPDX-License-Identifier: LGPL-2.1-only
# Copyright (C) 2024 Akshat Kotpalliwar
"""Tests for code generation."""

import pytest

from gc_monitor.codegen import generate_monitoring_code


class TestCodeGeneration:
    """Tests for monitoring code generation."""

    def test_generates_valid_python(self):
        """Test that generated code is valid Python."""
        code = generate_monitoring_code()
        
        # Should compile without errors
        compile(code, '<string>', 'exec')

    def test_includes_gc_monitor_package(self):
        """Test that generated code imports from gc_monitor package."""
        code = generate_monitoring_code()
        assert 'gc_monitor' in code

    def test_includes_monitor_import(self):
        """Test that generated code imports GCMonitor."""
        code = generate_monitoring_code()
        assert 'from gc_monitor.monitor import GCMonitor' in code

    def test_config_values_injected(self):
        """Test that config values are properly injected."""
        code = generate_monitoring_code(
            interval=10.0,
            json_output=True,
            stats_only=True,
            alert_threshold_ms=200.0
        )
        
        assert "'interval': 10.0" in code
        assert "'json_output': True" in code
        assert "'stats_only': True" in code
        assert "'alert_threshold_ms': 200.0" in code

    def test_log_file_injection(self):
        """Test that log file path is properly injected."""
        code = generate_monitoring_code(log_file='/path/to/log.txt')
        assert "'/path/to/log.txt'" in code

    def test_log_file_none(self):
        """Test that None log file is handled."""
        code = generate_monitoring_code(log_file=None)
        assert "'log_file': None" in code

    def test_flamegraph_options(self):
        """Test flame graph options are injected."""
        code = generate_monitoring_code(
            flamegraph_file='flame.txt',
            flamegraph_bucket=10.0,
            terminal_flamegraph=True,
            terminal_flamegraph_width=120,
            terminal_flamegraph_color=True
        )
        
        assert "'flamegraph_file': 'flame.txt'" in code
        assert "'flamegraph_bucket': 10.0" in code
        assert "'terminal_flamegraph': True" in code
        assert "'terminal_flamegraph_width': 120" in code
        assert "'terminal_flamegraph_color': True" in code

    def test_duration_buckets_default(self):
        """Test default duration buckets."""
        code = generate_monitoring_code()
        assert "'duration_buckets': [1.0, 5.0, 20.0, 50.0, 100.0]" in code

    def test_duration_buckets_custom(self):
        """Test custom duration buckets."""
        code = generate_monitoring_code(duration_buckets=[1, 10, 100])
        assert "'duration_buckets': [1.0, 10.0, 100.0]" in code

    def test_duration_buckets_sorted_deduped(self):
        """Test that duration buckets are sorted and deduplicated."""
        code = generate_monitoring_code(duration_buckets=[100, 10, 10, 1])
        assert "'duration_buckets': [1.0, 10.0, 100.0]" in code

    def test_includes_runpy_for_execution(self):
        """Test that runpy is used for script execution."""
        code = generate_monitoring_code()
        assert 'import runpy' in code

    def test_includes_module_mode_handling(self):
        """Test that module mode (-m) is handled."""
        code = generate_monitoring_code()
        assert "first_arg == '-m'" in code
        assert 'run_module' in code

    def test_includes_script_mode_handling(self):
        """Test that script mode is handled."""
        code = generate_monitoring_code()
        assert 'run_path' in code

    def test_includes_finally_cleanup(self):
        """Test that cleanup happens in finally block."""
        code = generate_monitoring_code()
        assert 'finally:' in code
        assert 'stop_monitoring()' in code

    def test_includes_signal_handler(self):
        """Test that signal handler is included."""
        code = generate_monitoring_code()
        assert 'signal.SIGUSR1' in code
        assert 'show_stats_handler' in code


class TestCodeGenerationEdgeCases:
    """Edge case tests for code generation."""

    def test_empty_duration_buckets(self):
        """Test handling of empty duration buckets."""
        code = generate_monitoring_code(duration_buckets=[])
        # Should fall back to default
        assert "'duration_buckets': [1.0, 5.0, 20.0, 50.0, 100.0]" in code

    def test_negative_duration_buckets_filtered(self):
        """Test that negative buckets are filtered."""
        code = generate_monitoring_code(duration_buckets=[-1, 5, -10, 20])
        assert "'duration_buckets': [5.0, 20.0]" in code

    def test_special_chars_in_log_file(self):
        """Test handling of special characters in log file path."""
        code = generate_monitoring_code(log_file="/path/with spaces/log.txt")
        compile(code, '<string>', 'exec')  # Should still be valid Python

    def test_windows_path_handling(self):
        """Test handling of Windows-style paths."""
        code = generate_monitoring_code(log_file="C:\\Users\\test\\log.txt")
        compile(code, '<string>', 'exec')  # Should still be valid Python

