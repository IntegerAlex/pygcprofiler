# SPDX-License-Identifier: LGPL-2.1-only
# Copyright (C) 2024 Akshat Kotpalliwar

"""
Code generation for pygcprofiler injection
"""

from pathlib import Path
import textwrap


def generate_monitoring_code(**config):
    """Generate the Python code injected into the target process"""
    duration_buckets = config.get('duration_buckets') or [1, 5, 20, 50, 100]
    duration_buckets = sorted(set(float(x) for x in duration_buckets if x > 0))
    if not duration_buckets:
        duration_buckets = [1, 5, 20, 50, 100]

    package_root = Path(__file__).resolve().parent.parent
    package_root_literal = str(package_root).replace("\\", "\\\\")
    duration_buckets_literal = repr(duration_buckets)

    monitoring_code = textwrap.dedent(
        f"""
        import os
        import sys
        import traceback

        PACKAGE_ROOT = r"{package_root_literal}"
        if PACKAGE_ROOT and PACKAGE_ROOT not in sys.path:
            sys.path.insert(0, PACKAGE_ROOT)

        from gc_monitor.monitor import GCMonitor

        monitor_config = {{
            'interval': {config.get('interval', 5.0)},
            'json_output': {config.get('json_output', False)},
            'stats_only': {config.get('stats_only', False)},
            'dump_objects': {config.get('dump_objects', False)},
            'dump_garbage': {config.get('dump_garbage', False)},
            'log_file': {repr(config.get('log_file')) if config.get('log_file') else None},
            'alert_threshold_ms': {config.get('alert_threshold_ms', 50.0)},
            'flamegraph_file': {repr(config.get('flamegraph_file')) if config.get('flamegraph_file') else None},
            'flamegraph_bucket': {config.get('flamegraph_bucket', 5.0)},
            'duration_buckets': {duration_buckets_literal},
            'terminal_flamegraph': {config.get('terminal_flamegraph', False)},
            'terminal_flamegraph_width': {config.get('terminal_flamegraph_width', 80)},
            'terminal_flamegraph_color': {config.get('terminal_flamegraph_color', False)}
        }}

        print("GMEM Monitoring initialized", file=sys.stderr)
        monitor = GCMonitor(**monitor_config)

        try:
            script_path = sys.argv[1]
            script_args = sys.argv[2:]

            script_dir = os.path.dirname(os.path.abspath(script_path))
            if script_dir and script_dir not in sys.path:
                sys.path.insert(0, script_dir)

            sys.argv = [script_path] + script_args

            # Use runpy to execute the script as if it were run directly
            # This preserves __name__ == "__main__" behavior
            import runpy
            runpy.run_path(script_path, run_name="__main__")
        except Exception as exc:  # noqa: BLE001
            print(f"GMEM Error running script: {{exc}}", file=sys.stderr)
            traceback.print_exc()
            sys.exit(1)
        finally:
            monitor.stop_monitoring()
        """
    )

    return monitoring_code
