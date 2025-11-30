"""
Main entry point for pygcprofiler CLI
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

import sys
import os
import subprocess
import shlex
import signal

from .cli import parse_arguments, parse_duration_buckets
from .codegen import generate_monitoring_code


def main():
    """Main entry point for pygcprofiler CLI."""
    args = parse_arguments()

    if not args.command:
        # Friendly banner + usage when invoked without a subcommand
        print("pygcprofiler - See Python's garbage collector in action without getting in its way.", file=sys.stderr)
        print("Author: Akshat Kotpalliwar", file=sys.stderr)
        print("License: LGPL-2.1-only", file=sys.stderr)
        print("", file=sys.stderr)
        print("Usage:", file=sys.stderr)
        print("  pygcprofiler run <script.py> [args...]", file=sys.stderr)
        print("  pygcprofiler run -m <module> [args...]", file=sys.stderr)
        print("", file=sys.stderr)
        print("For help on options:", file=sys.stderr)
        print("  pygcprofiler --help", file=sys.stderr)
        sys.exit(1)

    if args.command == 'dashboard':
        try:
            from .dashboard.server import start_server
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

        # Enforce flag ordering: all pygcprofiler flags must appear BEFORE the script.
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
            "--prompt",
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
            print("Error: pygcprofiler flags must appear before the script path.", file=sys.stderr)
            print("Current invocation mixes pygcprofiler flags with script/module flags:", file=sys.stderr)
            print(f"  Misplaced: {' '.join(misplaced)}", file=sys.stderr)
            print("", file=sys.stderr)
            print("Correct examples:", file=sys.stderr)
            print("  pygcprofiler run --live --interval 1.0 test.py --your-script-flag --arg", file=sys.stderr)
            print("  pygcprofiler run --stats-only --prompt test.py", file=sys.stderr)
            sys.exit(2)

        # Check if running a module (-m) or a script file
        is_module = args.script == '-m'
        
        if not is_module and not os.path.exists(args.script):
            print(f"Error: Script file not found: {args.script}", file=sys.stderr)
            print("", file=sys.stderr)
            print("Troubleshooting:", file=sys.stderr)
            print("  - Check the file path is correct", file=sys.stderr)
            print("  - Use absolute path: pygcprofiler run /full/path/to/script.py", file=sys.stderr)
            print("  - For modules, use: pygcprofiler run -m module_name", file=sys.stderr)
            sys.exit(1)

        duration_buckets = parse_duration_buckets(getattr(args, 'duration_buckets', None))

        # Create the monitoring code
        monitoring_code = generate_monitoring_code(
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
            live_port=args.live_port,
            enable_prompt=getattr(args, 'prompt', False)
        )

        # Prepare the command to run Python with our monitoring code
        cmd = [
            sys.executable,
            '-c',
            monitoring_code,
            args.script
        ] + args.script_args

        # Do NOT dump the entire injected monitoring code to the terminal;
        # just show a concise, user-friendly message.
        display_cmd = [sys.executable, args.script] + args.script_args
        printable = " ".join(shlex.quote(arg) for arg in display_cmd)
        print(f"GMEM Running: {printable}", file=sys.stderr)

        # Optional: auto-start dashboard when live monitoring is enabled
        dashboard_proc = None
        if args.live:
            try:
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
                    str(8000),
                ]
                dashboard_proc = subprocess.Popen(dashboard_cmd)
                print(
                    f"GMEM Dashboard auto-started at http://{args.live_host}:8000 "
                    f"(UDP {args.live_host}:{args.live_port})",
                    file=sys.stderr,
                )
            except Exception as e:  # pragma: no cover - best-effort
                print(f"GMEM Warning: Failed to auto-start dashboard: {e}", file=sys.stderr)

        # Track the subprocess for signal forwarding
        process = None
        
        def signal_handler(signum, frame):
            """Forward signals to the subprocess for graceful shutdown."""
            if process is not None:
                try:
                    process.send_signal(signum)
                except (ProcessLookupError, OSError):
                    pass  # Process already terminated
        
        # Set up signal handlers for graceful shutdown
        original_sigint = signal.signal(signal.SIGINT, signal_handler)
        original_sigterm = signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            # Run the command
            process = subprocess.Popen(cmd)
            returncode = process.wait()
            sys.exit(returncode)
        except KeyboardInterrupt:
            print("\nGMEM Monitoring interrupted by user", file=sys.stderr)
            if process is not None:
                try:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                except (ProcessLookupError, OSError):
                    pass
            sys.exit(130)  # Standard exit code for SIGINT
        finally:
            # Restore original signal handlers
            signal.signal(signal.SIGINT, original_sigint)
            signal.signal(signal.SIGTERM, original_sigterm)

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


if __name__ == "__main__":
    main()
