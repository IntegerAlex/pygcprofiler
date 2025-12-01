# pygcprofiler

[![PyPI version](https://img.shields.io/pypi/v/pygcprofiler.svg)](https://pypi.org/project/pygcprofiler/)
[![PyPI downloads](https://img.shields.io/pypi/dm/pygcprofiler.svg)](https://pypi.org/project/pygcprofiler/)
[![PyPI - Monthly Downloads](https://img.shields.io/pypi/dm/pygcprofiler?label=downloads%2Fmonth)](https://pypi.org/project/pygcprofiler/)
[![License: LGPL v2.1](https://img.shields.io/badge/License-LGPL_v2.1-blue.svg)](https://www.gnu.org/licenses/lgpl-2.1)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![GitHub stars](https://img.shields.io/github/stars/IntegerAlex/pygcprofiler.svg?style=social&label=Star)](https://github.com/IntegerAlex/pygcprofiler)
[![GitHub forks](https://img.shields.io/github/forks/IntegerAlex/pygcprofiler.svg?style=social&label=Fork)](https://github.com/IntegerAlex/pygcprofiler)
[![GitHub issues](https://img.shields.io/github/issues/IntegerAlex/pygcprofiler.svg)](https://github.com/IntegerAlex/pygcprofiler/issues)
[![GitHub license](https://img.shields.io/github/license/IntegerAlex/pygcprofiler.svg)](https://github.com/IntegerAlex/pygcprofiler/blob/main/LICENSE)

**See Python's garbage collector in action without getting in its way.**

A zero-overhead GC monitoring tool designed for production applications. Monitor garbage collection events, identify performance bottlenecks, and get actionable optimization recommendations—all without affecting your application's behavior.

## ✨ Key Features

- **Zero Runtime Overhead**: Callback only records timestamps and counters—no I/O, no memory checks during GC
- **Non-Intrusive**: Never modifies GC thresholds, never forces collections, purely observational
- **Production-Ready**: All output buffered until shutdown, no background threads
- **Rich Diagnostics**: ASCII flame graphs, threshold alerts, AI-powered optimization prompts
- **Flexible Output**: Human-readable or JSON format, file logging, configurable alerts

## 📦 Installation

```bash
# From PyPI (when published)
pip install pygcprofiler

# From source
pip install -e .

# With development dependencies
pip install -e ".[dev]"
```

**Requirements:** Python 3.10+ and `psutil` (installed automatically)

## 🚀 Quick Start

### Basic Usage

```bash
# Monitor any Python script (all pygcprofiler flags must come BEFORE the script)
pygcprofiler run [pygcprofiler-flags...] your_script.py [script-args...]

# Or use the alias
gc-monitor run [pygcprofiler-flags...] your_script.py [script-args...]

# Pass arguments to your script
pygcprofiler run server.py --port 8000 --debug
```

### With Web Frameworks

```bash
# Uvicorn (ASGI)
pygcprofiler run -m uvicorn main:app --host 0.0.0.0 --port 8000

# Gunicorn (WSGI)
pygcprofiler run -m gunicorn app:app --workers 4 --bind 0.0.0.0:8000

# Flask development server
pygcprofiler run app.py

# Django
pygcprofiler run manage.py runserver
```

### Production Monitoring

```bash
# JSON output for log aggregation (ELK, Splunk, etc.)
pygcprofiler run --json --log-file gc-events.json -m uvicorn main:app

# Minimal output, only show summary at shutdown
pygcprofiler run --stats-only -m uvicorn main:app

# Custom alert threshold (default: 50ms)
pygcprofiler run --alert-threshold-ms 100 -m uvicorn main:app
```

### Flame Graph Visualization

```bash
# ASCII flame graph in terminal
pygcprofiler run --terminal-flamegraph --terminal-flamegraph-color app.py

# Export for external visualization tools
pygcprofiler run --flamegraph-file gc-flame.txt app.py

# Custom bucket size for time grouping
pygcprofiler run --terminal-flamegraph --flamegraph-bucket 10 app.py
```

## 📊 Example Output

```
GMEM Monitoring initialized (Zero Runtime Overhead)
GMEM Running: python -c '...' your_script.py

GMEM GC STOP  | Gen: 0 | Duration: 0.2ms | Collected: 156 | Uncollectable: 0
GMEM GC STOP  | Gen: 0 | Duration: 0.3ms | Collected: 203 | Uncollectable: 0
GMEM GC STOP  | Gen: 1 | Duration: 1.2ms | Collected: 1024 | Uncollectable: 0
GMEM ALERT | Gen 2 pause 52.3ms exceeded 50.0ms threshold
GMEM GC STOP  | Gen: 2 | Duration: 52.3ms | Collected: 15234 | Uncollectable: 0

=== GC MONITORING SUMMARY ===
Total GC collections: 847
Total GC time: 312.5ms
Average GC duration: 0.4ms
Maximum GC duration: 52.3ms

Collections by generation:
  Generation 0: 789 collections
  Generation 1: 52 collections
  Generation 2: 6 collections

=== GC THRESHOLD RECOMMENDATIONS ===
- Generation 2 average pause 28.4ms. Consider reducing long-lived allocations...
```

## ⚙️ Command Line Options

| Option | Default | Description |
|--------|---------|-------------|
| `--interval` | 5.0 | Snapshot interval in seconds |
| `--json` | false | Output in JSON format |
| `--stats-only` | false | Only show summary, not individual events |
| `--dump-objects` | false | Dump object type analysis at shutdown |
| `--dump-garbage` | false | Show uncollectable objects (enables DEBUG_SAVEALL) |
| `--log-file` | none | Write output to file |
| `--alert-threshold-ms` | 50.0 | Alert when GC pause exceeds this (ms) |
| `--flamegraph-file` | none | Write flame graph data to file |
| `--flamegraph-bucket` | 5.0 | Time bucket size for flame graph (seconds) |
| `--terminal-flamegraph` | false | Show ASCII flame graph in terminal |
| `--terminal-flamegraph-width` | 80 | Width of terminal flame graph |
| `--terminal-flamegraph-color` | false | Use ANSI colors in flame graph |
| `--duration-buckets` | 1,5,20,50,100 | GC pause duration buckets (ms) |
| `--prompt` | false | Generate and display AI optimization prompt at shutdown |

## 🔧 Programmatic Usage (Deprecated)

Programmatic use of `pygcprofiler` (importing `GCMonitor`, `GCStatistics`, or `GCLogger` from `gc_monitor`) is **deprecated**.
Most Python language servers (Pyright, Pylance, etc.) will now surface deprecation warnings when you import or instantiate these classes.
Please prefer the CLI entrypoints instead:

```bash
pygcprofiler run your_script.py
gc-monitor run -m uvicorn main:app
```

## 🎯 Design Principles

pygcprofiler follows strict **zero-runtime-interference** principles:

### What We Do ✅
```python
gc.callbacks.append(monitor._gc_callback)  # Pure observation
time.perf_counter()  # High-precision timing
```

### What We Never Do ❌
```python
gc.set_threshold(...)  # Never modify GC behavior
gc.collect()           # Never force collections
gc.freeze()            # Never freeze objects
gc.get_objects()       # Never scan object graphs during runtime
print(...)             # Never do I/O in callbacks
```

### Performance Characteristics

- **< 0.1% runtime overhead** — callback is just timestamp recording
- **Zero additional GC pressure** — no temporary objects in callbacks
- **Same latency profile** — no I/O or expensive operations during runtime
- **Identical memory usage** — no allocations that could affect GC behavior

## 🔍 Troubleshooting

### "Script file not found"

Ensure the script path is correct and accessible:

```bash
# Use absolute path
pygcprofiler run /full/path/to/script.py

# Or run from the script's directory
cd /path/to/project && pygcprofiler run script.py
```

### Module mode not working

For modules, use `-m` as the first argument after `run`:

```bash
# Correct
pygcprofiler run -m uvicorn main:app

# Wrong
pygcprofiler run uvicorn main:app
```

### No GC events showing

If your application doesn't allocate enough objects to trigger GC:

```bash
# Lower the snapshot interval
pygcprofiler run app.py --interval 1

# Or run with object dump to see current state
pygcprofiler run app.py --dump-objects
```

### High memory usage in logs

For high-throughput applications, reduce log verbosity:

```bash
# Only show summary at shutdown
pygcprofiler run -m uvicorn main:app --stats-only

# Or increase alert threshold to reduce noise
pygcprofiler run -m uvicorn main:app --alert-threshold-ms 200
```

## 🔐 Security Considerations

- **Log files may contain timing information** that could reveal application behavior patterns
- **Object dumps (`--dump-objects`)** show type names but not object contents
- **Never log to world-readable locations** in production
- **Use `--stats-only`** in sensitive environments to minimize data exposure

```bash
# Secure production setup
pygcprofiler run -m uvicorn main:app \
    --stats-only \
    --log-file /var/log/myapp/gc.log \
    --json
```

## 📈 Interpreting Results

### GC Generations

- **Gen 0**: Short-lived objects, collected frequently (< 1ms typical)
- **Gen 1**: Objects that survived Gen 0, collected less often
- **Gen 2**: Long-lived objects, collected rarely but takes longest

### Warning Signs

| Metric | Concern Level | Action |
|--------|---------------|--------|
| Gen 2 > 10% of collections | 🟡 Medium | Consider `gc.freeze()` after init |
| Max pause > 50ms | 🟠 High | Tune thresholds, reduce allocations |
| GC CPU > 5% | 🔴 Critical | Major optimization needed |
| Uncollectable > 0 | 🟡 Medium | Check for reference cycles |

### Recommended Optimizations

```python
import gc

# After application initialization
gc.collect(2)  # Full collection
gc.freeze()    # Freeze startup objects

# Tune thresholds for your workload
gc.set_threshold(50000, 10, 10)  # Reduce collection frequency
```

## 🏗️ Architecture

```
src/gc_monitor/
├── __init__.py      # Package metadata
├── __main__.py      # CLI entry point
├── cli.py           # Argument parsing
├── codegen.py       # Injection code generation
├── monitor.py       # Core GC monitoring (zero-overhead)
├── logging.py       # Event logging utilities
├── stats.py         # Statistics and recommendations
├── flamegraph.py    # Flame graph rendering
├── memory.py        # Memory utilities
└── prompts.py       # AI optimization prompts
```

## 🧪 Development

```bash
# Clone the repository
git clone https://github.com/IntegerAlex/pygcprofiler.git
cd pygcprofiler

# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run linter
ruff check src/ tests/

# Type checking
mypy src/
```

## 📄 License

This project is licensed under the **GNU Lesser General Public License v2.1** (LGPL-2.1).

You may use this library in proprietary applications, but modifications to the library itself must be shared under the same license. See [LICENSE](LICENSE) for details.

```
pygcprofiler - Python Garbage Collection Profiling Tool
Copyright (C) 2024 Akshat Kotpalliwar

This library is free software; you can redistribute it and/or modify it
under the terms of the GNU Lesser General Public License as published by
the Free Software Foundation; either version 2.1 of the License, or
(at your option) any later version.
```

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📝 Changelog

See [CHANGELOG.md](CHANGELOG.md) for version history and release notes.
