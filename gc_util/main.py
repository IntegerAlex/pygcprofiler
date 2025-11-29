"""Main entry point for gc-util.py."""

import sys
import os
import subprocess
import shlex

from .cli import parse_arguments
from .codegen import create_monitoring_code


def main():
    """Main entry point."""
    args = parse_arguments()
    
    if not args.command:
        # Friendly banner + usage when invoked without a subcommand
        print("pygcprofiler - See Python's garbage collector in action without getting in its way.", file=sys.stderr)
        print("Author: Akshat Kotpalliwar", file=sys.stderr)
        print("License: LGPL-2.1-only", file=sys.stderr)
        print("", file=sys.stderr)
        print("Usage:", file=sys.stderr)
        print("  gc-util.py run <script.py> [args...]", file=sys.stderr)
        print("  gc-util.py run -m <module> [args...]", file=sys.stderr)
        print("  gc-util.py dashboard [--host HOST] [--port PORT] [--udp-port UDP_PORT]", file=sys.stderr)
        print("", file=sys.stderr)
        print("For help on options:", file=sys.stderr)
        print("  gc-util.py --help", file=sys.stderr)
        sys.exit(1)
    
    if args.command == 'dashboard':
        try:
            from gc_monitor.dashboard.server import start_server
            start_server(host=args.host, http_port=args.port, udp_port=args.udp_port)
        except ImportError:
            print("Error: Dashboard dependencies not found.", file=sys.stderr)
            print("Please install with: pip install fastapi uvicorn", file=sys.stderr)
            sys.exit(1)
        except KeyboardInterrupt:
            sys.exit(0)
        return
    
    if args.command == 'run':
        # Friendly banner on successful invocations, similar to tools like gdb.
        print("pygcprofiler - See Python's garbage collector in action without getting in its way.", file=sys.stderr)
        print("Author: Akshat Kotpalliwar | License: LGPL-2.1-only", file=sys.stderr)
        print("", file=sys.stderr)

        # Enforce flag ordering: all gc-util/pygcprofiler flags must appear BEFORE the script.
        tool_flags = {
            "--interval",
            "--json",
            "--stats-only",
            "--dump-objects",
            "--dump-garbage",
            "--log-file",
            "--alert-threshold-ms",
            "--flamegraph-file",
            "--flamegraph-bucket",
            "--duration-buckets",
            "--terminal-flamegraph",
            "--terminal-flamegraph-width",
            "--terminal-flamegraph-color",
            "--live",
            "--live-host",
            "--live-port",
        }
        misplaced = []
        for arg in args.script_args:
            if not arg.startswith("--"):
                continue
            for flag in tool_flags:
                if arg == flag or arg.startswith(flag + "="):
                    misplaced.append(arg)
                    break
        if misplaced:
            print("Error: gc-util/pygcprofiler flags must appear before the script path.", file=sys.stderr)
            print("Current invocation mixes monitoring flags with script/module flags:", file=sys.stderr)
            print(f"  Misplaced: {' '.join(misplaced)}", file=sys.stderr)
            print("", file=sys.stderr)
            print("Correct examples:", file=sys.stderr)
            print("  gc-util.py run --live --interval 1.0 test.py --your-script-flag --arg", file=sys.stderr)
            print("  gc-util.py run --stats-only test.py", file=sys.stderr)
            sys.exit(2)
        
        if not os.path.exists(args.script):
            print(f"Error: Script file not found: {args.script}", file=sys.stderr)
            sys.exit(1)
        
        duration_buckets = []
        if getattr(args, 'duration_buckets', None):
            for part in args.duration_buckets.split(','):
                part = part.strip()
                if not part:
                    continue
                try:
                    value = float(part)
                except ValueError:
                    continue
                if value > 0:
                    duration_buckets.append(value)
        
        # Create the monitoring code
        monitoring_code = create_monitoring_code(
            interval=args.interval,
            json_output=args.json,
            stats_only=args.stats_only,
            dump_objects=args.dump_objects,
            dump_garbage=args.dump_garbage,
            log_file=args.log_file,
            alert_threshold_ms=args.alert_threshold_ms,
            flamegraph_file=args.flamegraph_file,
            flamegraph_bucket=args.flamegraph_bucket,
            duration_buckets=duration_buckets or None,
            terminal_flamegraph=args.terminal_flamegraph,
            terminal_flamegraph_width=args.terminal_flamegraph_width,
            terminal_flamegraph_color=args.terminal_flamegraph_color,
            live_monitoring=args.live,
            live_host=args.live_host,
            live_port=args.live_port
        )
        
        # Prepare the command to run Python with our monitoring code
        cmd = [
            sys.executable,
            '-c',
            monitoring_code,
            args.script
        ] + args.script_args

        # Do NOT print the injected monitoring code. Show only a concise view
        # of what the user cares about: their Python executable + script.
        visible_cmd = [sys.executable, args.script] + args.script_args
        printable = " ".join(shlex.quote(arg) for arg in visible_cmd)
        print(f"GMEM Running: {printable}", file=sys.stderr)

        # Optional: auto-start dashboard when live monitoring is enabled
        dashboard_proc = None
        if args.live:
            try:
                http_port = os.environ.get("PYGCPROFILER_DASHBOARD_PORT", "8000")
                dashboard_cmd = [
                    sys.executable,
                    "-m",
                    "gc_monitor",
                    "dashboard",
                    "--host",
                    args.live_host,
                    "--udp-port",
                    str(args.live_port),
                    "--port",
                    http_port,
                ]
                dashboard_proc = subprocess.Popen(dashboard_cmd)
                print(
                    f"GMEM Dashboard auto-started at http://{args.live_host}:{http_port} "
                    f"(UDP {args.live_host}:{args.live_port})",
                    file=sys.stderr,
                )
            except Exception as e:  # pragma: no cover - best-effort
                print(f"GMEM Warning: Failed to auto-start dashboard: {e}", file=sys.stderr)
        
        try:
            # Run the command
            result = subprocess.run(cmd, check=False)
            sys.exit(result.returncode)
        except KeyboardInterrupt:
            print("\nGMEM Monitoring interrupted by user", file=sys.stderr)
            sys.exit(130)  # Standard exit code for interrupted processes
        finally:
            # Stop auto-started dashboard if it's still running
            if dashboard_proc is not None:
                try:
                    if dashboard_proc.poll() is None:
                        dashboard_proc.terminate()
                        try:
                            dashboard_proc.wait(timeout=5)
                        except (subprocess.TimeoutExpired, KeyboardInterrupt):
                            dashboard_proc.kill()
                except Exception:
                    # Best-effort cleanup; ignoring errors here prevents masking original exit causes
                    pass

