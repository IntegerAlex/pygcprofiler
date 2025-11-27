# pygcprofiler

See Python's garbage collector in action without getting in its way.

## Features

- Real-time GC event monitoring
- Detailed statistics and performance metrics
- ASCII flame graph visualization
- Threshold-based alerting
- Memory usage tracking
- Object type analysis
- JSON output support

## Installation

```bash
pip install -e .
```

## Usage

Run any Python script with garbage collection profiling:

```bash
pygcprofiler run your_script.py [args...]
```

### Examples

```bash
# Basic profiling
pygcprofiler run my_app.py

# With custom options
pygcprofiler run server.py --interval 2 --alert-threshold-ms 100

# Generate flame graph
pygcprofiler run app.py --terminal-flamegraph --flamegraph-file gc-data.txt

# JSON output
pygcprofiler run script.py --json --log-file output.json
```

### Command Line Options

- `--interval`: Snapshot interval in seconds (default: 5.0)
- `--json`: Output in JSON format
- `--stats-only`: Only show statistics, not individual events
- `--dump-objects`: Dump object information at the end
- `--dump-garbage`: Dump uncollectable objects
- `--log-file`: Log output to file
- `--alert-threshold-ms`: Alert threshold for GC pauses (default: 50ms)
- `--flamegraph-file`: Write flame graph data to file
- `--terminal-flamegraph`: Show ASCII flame graph in terminal
- `--terminal-flamegraph-width`: Width of flame graph (default: 80)
- `--terminal-flamegraph-color`: Use ANSI colors in flame graph
- `--duration-buckets`: Custom GC duration buckets (comma-separated)

## Architecture

The project is organized into modular components:

- `cli.py`: Command-line interface and argument parsing
- `monitor.py`: Core GC monitoring coordination
- `logging.py`: Event logging utilities
- `stats.py`: Statistics calculation and recommendations
- `flamegraph.py`: Flame graph rendering and data collection
- `codegen.py`: Code generation for injection into target processes

## Development

```bash
# Install in development mode
pip install -e .

# Run tests
pygcprofiler run server.py --stats-only
```

## License

This project is licensed under the LGPL-2.1-only license. See the LICENSE file for details.
