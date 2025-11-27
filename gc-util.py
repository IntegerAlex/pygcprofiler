#!/usr/bin/env python3
"""
gc-util.py - Python Garbage Collection Monitoring Utility

A CLI wrapper that monitors garbage collection events for any Python application.
This version properly injects monitoring code into the target process.

Zero Runtime Interference Design:
- Callback only records timestamps and counters (no I/O, no memory checks)
- Uses time.perf_counter() for high-precision, low-overhead timing
- All output is buffered and written only at shutdown
- No gc.get_objects() or memory measurement during runtime

Usage:
  gc-util.py run <script.py> [script_args...] [options]
  gc-util.py dashboard [--host HOST] [--port PORT] [--udp-port UDP_PORT]

Examples:
  gc-util.py run my_app.py --arg1 value1
  gc-util.py run server.py --port 8000 --debug
  gc-util.py dashboard
  gc-util.py dashboard --port 8080 --udp-port 9999
"""

from gc_util.main import main

if __name__ == "__main__":
    main()
