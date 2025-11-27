# SPDX-License-Identifier: LGPL-2.1-only
# Copyright (C) 2024 Akshat Kotpalliwar
"""Tests for CLI argument parsing."""

import sys
import pytest
from unittest.mock import patch

from gc_monitor.cli import parse_arguments, parse_duration_buckets


class TestParseDurationBuckets:
    """Tests for duration bucket parsing."""

    def test_default_buckets(self):
        """Test parsing default bucket string."""
        result = parse_duration_buckets("1,5,20,50,100")
        assert result == [1.0, 5.0, 20.0, 50.0, 100.0]

    def test_empty_string(self):
        """Test parsing empty string."""
        result = parse_duration_buckets("")
        assert result == []

    def test_none_input(self):
        """Test parsing None."""
        result = parse_duration_buckets(None)
        assert result == []

    def test_whitespace_handling(self):
        """Test that whitespace is handled correctly."""
        result = parse_duration_buckets(" 1 , 5 , 10 ")
        assert result == [1.0, 5.0, 10.0]

    def test_invalid_values_skipped(self):
        """Test that invalid values are skipped."""
        result = parse_duration_buckets("1,invalid,5,abc,10")
        assert result == [1.0, 5.0, 10.0]

    def test_negative_values_skipped(self):
        """Test that negative values are skipped."""
        result = parse_duration_buckets("1,-5,10,-20,50")
        assert result == [1.0, 10.0, 50.0]

    def test_zero_skipped(self):
        """Test that zero is skipped."""
        result = parse_duration_buckets("0,1,5")
        assert result == [1.0, 5.0]

    def test_float_values(self):
        """Test parsing float values."""
        result = parse_duration_buckets("0.5,1.5,2.5")
        assert result == [0.5, 1.5, 2.5]


class TestParseArguments:
    """Tests for CLI argument parsing."""

    def test_run_command_basic(self):
        """Test basic run command parsing."""
        with patch.object(sys, 'argv', ['pygcprofiler', 'run', 'script.py']):
            args = parse_arguments()
            assert args.command == 'run'
            assert args.script == 'script.py'
            assert args.script_args == []

    def test_run_with_script_args(self):
        """Test run command with script arguments."""
        with patch.object(sys, 'argv', ['pygcprofiler', 'run', 'script.py', '--port', '8000']):
            args = parse_arguments()
            assert args.script == 'script.py'
            assert args.script_args == ['--port', '8000']

    def test_default_values(self):
        """Test default argument values."""
        with patch.object(sys, 'argv', ['pygcprofiler', 'run', 'script.py']):
            args = parse_arguments()
            assert args.interval == 5.0
            assert args.json is False
            assert args.stats_only is False
            assert args.dump_objects is False
            assert args.dump_garbage is False
            assert args.log_file is None
            assert args.alert_threshold_ms == 50.0
            assert args.flamegraph_file is None
            assert args.flamegraph_bucket == 5.0
            assert args.terminal_flamegraph is False
            assert args.terminal_flamegraph_width == 80
            assert args.terminal_flamegraph_color is False

    def test_custom_interval(self):
        """Test custom interval setting - options must come before script."""
        # Note: With REMAINDER, options after script are captured as script_args
        # So we test that options before script work correctly
        with patch.object(sys, 'argv', ['pygcprofiler', 'run', '--interval', '2.5', 'script.py']):
            args = parse_arguments()
            assert args.interval == 2.5
            assert args.script == 'script.py'

    def test_json_flag(self):
        """Test JSON output flag."""
        with patch.object(sys, 'argv', ['pygcprofiler', 'run', '--json', 'script.py']):
            args = parse_arguments()
            assert args.json is True

    def test_stats_only_flag(self):
        """Test stats-only flag."""
        with patch.object(sys, 'argv', ['pygcprofiler', 'run', '--stats-only', 'script.py']):
            args = parse_arguments()
            assert args.stats_only is True

    def test_dump_flags(self):
        """Test dump flags."""
        with patch.object(sys, 'argv', ['pygcprofiler', 'run', '--dump-objects', '--dump-garbage', 'script.py']):
            args = parse_arguments()
            assert args.dump_objects is True
            assert args.dump_garbage is True

    def test_log_file(self):
        """Test log file argument."""
        with patch.object(sys, 'argv', ['pygcprofiler', 'run', '--log-file', 'output.log', 'script.py']):
            args = parse_arguments()
            assert args.log_file == 'output.log'

    def test_alert_threshold(self):
        """Test alert threshold argument."""
        with patch.object(sys, 'argv', ['pygcprofiler', 'run', '--alert-threshold-ms', '100', 'script.py']):
            args = parse_arguments()
            assert args.alert_threshold_ms == 100.0

    def test_flamegraph_options(self):
        """Test flame graph options."""
        with patch.object(sys, 'argv', [
            'pygcprofiler', 'run',
            '--flamegraph-file', 'flame.txt',
            '--flamegraph-bucket', '10',
            '--terminal-flamegraph',
            '--terminal-flamegraph-width', '120',
            '--terminal-flamegraph-color',
            'script.py'
        ]):
            args = parse_arguments()
            assert args.flamegraph_file == 'flame.txt'
            assert args.flamegraph_bucket == 10.0
            assert args.terminal_flamegraph is True
            assert args.terminal_flamegraph_width == 120
            assert args.terminal_flamegraph_color is True

    def test_duration_buckets(self):
        """Test duration buckets argument."""
        with patch.object(sys, 'argv', ['pygcprofiler', 'run', '--duration-buckets', '1,10,100', 'script.py']):
            args = parse_arguments()
            assert args.duration_buckets == '1,10,100'

    def test_module_mode(self):
        """Test module mode (-m) parsing using -- separator."""
        # Note: -m looks like an option to argparse, so we use -- to separate
        # or place it as part of script_args after a script placeholder
        with patch.object(sys, 'argv', ['pygcprofiler', 'run', '--', '-m', 'uvicorn', 'main:app']):
            args = parse_arguments()
            assert args.script == '-m'
            assert args.script_args == ['uvicorn', 'main:app']

    def test_script_args_preserved(self):
        """Test that script arguments are correctly preserved."""
        with patch.object(sys, 'argv', ['pygcprofiler', 'run', '--stats-only', 'script.py', '--port', '8000', '--debug']):
            args = parse_arguments()
            assert args.stats_only is True
            assert args.script == 'script.py'
            assert args.script_args == ['--port', '8000', '--debug']

    def test_mixed_options_and_script_args(self):
        """Test that pygcprofiler options before script and script args after are handled."""
        with patch.object(sys, 'argv', [
            'pygcprofiler', 'run',
            '--json', '--alert-threshold-ms', '75',
            'app.py',
            '--host', '0.0.0.0', '--port', '8000'
        ]):
            args = parse_arguments()
            assert args.json is True
            assert args.alert_threshold_ms == 75.0
            assert args.script == 'app.py'
            assert args.script_args == ['--host', '0.0.0.0', '--port', '8000']
