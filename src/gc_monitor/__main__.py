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
        print("Error: No command specified. Use 'run'", file=sys.stderr)
        print("Usage: pygcprofiler run <script.py> [args...]", file=sys.stderr)
        print("       pygcprofiler run -m <module> [args...]", file=sys.stderr)
        sys.exit(1)

    if args.command == 'run':
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
            terminal_flamegraph_color=args.terminal_flamegraph_color
        )

        # Prepare the command to run Python with our monitoring code
        cmd = [
            sys.executable,
            '-c',
            monitoring_code,
            args.script
        ] + args.script_args

        print(f"GMEM Running: {' '.join(shlex.quote(arg) for arg in cmd[:4])}...", file=sys.stderr)

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


if __name__ == "__main__":
    main()
