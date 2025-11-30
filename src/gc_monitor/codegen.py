"""
Code generation for pygcprofiler injection
Copyright (C) 2024  Akshat Kotpalliwar

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, see <https://www.gnu.org/licenses/>.
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
            'terminal_flamegraph_color': {config.get('terminal_flamegraph_color', False)},
            'live_monitoring': {config.get('live_monitoring', False)},
            'live_host': {repr(config.get('live_host', '127.0.0.1'))},
            'live_port': {config.get('live_port', 8989)},
            'enable_prompt': {config.get('enable_prompt', False)}
        }}

        print("GMEM Monitoring initialized", file=sys.stderr)
        monitor = GCMonitor(**monitor_config)
        
        # Register signal handler for long-running processes (e.g., uvicorn/gunicorn)
        # This allows showing stats on SIGUSR1 without stopping the server
        import signal
        def show_stats_handler(signum, frame):
            try:
                if hasattr(monitor, 'stats'):
                    summary = monitor.stats.get_summary_stats()
                    print("\\n=== GC STATS (SIGUSR1) ===", file=sys.stderr)
                    print(f"Collections: {{summary['total_collections']}}, "
                          f"Max pause: {{summary['max_duration']:.1f}}ms, "
                          f"Avg: {{summary['average_duration']:.1f}}ms", file=sys.stderr)
            except Exception:
                pass  # Ignore errors in signal handler
        
        try:
            signal.signal(signal.SIGUSR1, show_stats_handler)
        except (AttributeError, ValueError):
            # SIGUSR1 not available on Windows
            pass

        try:
            first_arg = sys.argv[1]
            script_args = sys.argv[2:]
            
            import runpy
            
            # Check if running a module (-m) or a script file
            if first_arg == '-m':
                # Module mode: python -m uvicorn app:app
                if not script_args:
                    print("GMEM Error: Module name required after -m", file=sys.stderr)
                    sys.exit(1)
                module_name = script_args[0]
                module_args = script_args[1:]
                sys.argv = ['-m', module_name] + module_args
                runpy.run_module(module_name, run_name="__main__")
            else:
                # Script file mode: python script.py
                script_path = first_arg
                script_dir = os.path.dirname(os.path.abspath(script_path))
                if script_dir and script_dir not in sys.path:
                    sys.path.insert(0, script_dir)
                
                sys.argv = [script_path] + script_args
                # Use runpy to execute the script as if it were run directly
                # This preserves __name__ == "__main__" behavior
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
