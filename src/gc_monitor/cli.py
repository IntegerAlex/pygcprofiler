# SPDX-License-Identifier: LGPL-2.1-only
# Copyright (C) 2024 Akshat Kotpalliwar

"""
Command Line Interface for pygcprofiler
"""

import argparse
import sys


def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description='See Python\'s garbage collector in action without getting in its way.',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  pygcprofiler run my_script.py
  pygcprofiler run server.py --interval 2 --terminal-flamegraph
  pygcprofiler run app.py --alert-threshold-ms 100 --dump-objects
        '''
    )

    subparsers = parser.add_subparsers(dest='command', help='Commands')
    run_parser = subparsers.add_parser('run', help='Run a Python script with GC monitoring')

    run_parser.add_argument('script', help='Python script to run')
    run_parser.add_argument('script_args', nargs=argparse.REMAINDER,
                          help='Arguments to pass to the script')

    # Monitoring options
    run_parser.add_argument('--interval', type=float, default=5.0,
                          help='Interval in seconds for periodic snapshots (default: 5.0)')
    run_parser.add_argument('--json', action='store_true',
                          help='Output in JSON format instead of human-readable')
    run_parser.add_argument('--stats-only', action='store_true',
                          help='Only show statistics, not individual GC events')
    run_parser.add_argument('--dump-objects', action='store_true',
                          help='Dump object information at the end')
    run_parser.add_argument('--dump-garbage', action='store_true',
                          help='Dump uncollectable objects (enables DEBUG_SAVEALL)')
    run_parser.add_argument('--log-file', help='Log output to file')
    run_parser.add_argument('--alert-threshold-ms', type=float, default=50.0,
                          help='Emit alerts when a GC pause exceeds this duration (ms)')
    run_parser.add_argument('--flamegraph-file',
                          help='Write collapsed stack-compatible flame graph data for GC events')
    run_parser.add_argument('--flamegraph-bucket', type=float, default=5.0,
                          help='Bucket size in seconds for grouping GC flame graph samples (default: 5s)')
    run_parser.add_argument('--duration-buckets', default='1,5,20,50,100',
                          help='Comma-separated GC pause bucket boundaries in ms (default: 1,5,20,50,100)')
    run_parser.add_argument('--terminal-flamegraph', action='store_true',
                          help='Render an ASCII flame graph summary directly in the terminal')
    run_parser.add_argument('--terminal-flamegraph-width', type=int, default=80,
                          help='Width of the terminal flame graph in characters (default: 80)')
    run_parser.add_argument('--terminal-flamegraph-color', action='store_true',
                          help='Use ANSI colors when rendering the terminal flame graph (requires TTY)')

    return parser.parse_args()


def parse_duration_buckets(duration_buckets_str):
    """Parse duration buckets from command line string"""
    duration_buckets = []
    if duration_buckets_str:
        for part in duration_buckets_str.split(','):
            part = part.strip()
            if not part:
                continue
            try:
                value = float(part)
            except ValueError:
                continue
            if value > 0:
                duration_buckets.append(value)
    return duration_buckets
