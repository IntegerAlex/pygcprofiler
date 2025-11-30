"""CLI argument parsing for gc-util.py."""

import argparse


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description='Python Garbage Collection Monitoring Utility (Zero Runtime Overhead)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  gc-util.py run my_script.py
  gc-util.py run --live my_script.py
  gc-util.py run --live server.py --port 8000 --debug
  gc-util.py run app.py --interval 2 --dump-objects
  gc-util.py dashboard
  gc-util.py dashboard --port 8080 --udp-port 9999
        '''
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Commands')
    
    # Dashboard command
    dash_parser = subparsers.add_parser('dashboard', help='Start the real-time visualization dashboard')
    dash_parser.add_argument('--host', default='127.0.0.1', help='Host to bind the dashboard server (default: 127.0.0.1)')
    dash_parser.add_argument('--port', type=int, default=8000, help='Port for the web dashboard (default: 8000)')
    dash_parser.add_argument('--udp-port', type=int, default=8989, help='Port to listen for GC events (default: 8989)')
    
    # Run command
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
    
    # Live monitoring options
    run_parser.add_argument('--live', action='store_true',
                          help='Enable live monitoring via UDP (default: 127.0.0.1:8989)')
    run_parser.add_argument('--live-host', default='127.0.0.1',
                          help='Host to send live UDP events to (default: 127.0.0.1)')
    run_parser.add_argument('--live-port', type=int, default=8989,
                          help='Port to send live UDP events to (default: 8989)')
    
    # AI prompt generation
    run_parser.add_argument('--prompt', action='store_true',
                          help='Generate and display AI optimization prompt at shutdown')
    
    return parser.parse_args()

