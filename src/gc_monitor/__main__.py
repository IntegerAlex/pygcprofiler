# SPDX-License-Identifier: LGPL-2.1-only
# Copyright (C) 2024 Akshat Kotpalliwar

"""
Main entry point for pygcprofiler CLI
"""

import sys
import os
import subprocess
import shlex

from .cli import parse_arguments, parse_duration_buckets
from .codegen import generate_monitoring_code


def main():
    args = parse_arguments()

    if not args.command:
        print("Error: No command specified. Use 'run'", file=sys.stderr)
        sys.exit(1)

    if args.command == 'run':
        if not os.path.exists(args.script):
            print(f"Error: Script file not found: {args.script}", file=sys.stderr)
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

        print(f"GMEM Running: {' '.join(shlex.quote(arg) for arg in cmd)}", file=sys.stderr)

        try:
            # Run the command
            result = subprocess.run(cmd, check=False)
            sys.exit(result.returncode)
        except KeyboardInterrupt:
            print("\nGMEM Monitoring interrupted by user", file=sys.stderr)
            sys.exit(130)  # Standard exit code for interrupted processes


if __name__ == "__main__":
    main()
