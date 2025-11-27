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
        print("Error: No command specified. Use 'run' or 'dashboard'", file=sys.stderr)
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
        # Check if --live was accidentally passed as a script argument
        if '--live' in args.script_args:
            print("Warning: --live flag should come before the script name.", file=sys.stderr)
            print("Correct usage: gc-util.py run --live script.py", file=sys.stderr)
            print("Enabling live monitoring anyway...", file=sys.stderr)
            args.live = True
            args.script_args = [a for a in args.script_args if a != '--live']
        
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
        
        print(f"GMEM Running: {' '.join(shlex.quote(arg) for arg in cmd)}", file=sys.stderr)
        
        try:
            # Run the command
            result = subprocess.run(cmd, check=False)
            sys.exit(result.returncode)
        except KeyboardInterrupt:
            print("\nGMEM Monitoring interrupted by user", file=sys.stderr)
            sys.exit(130)  # Standard exit code for interrupted processes

