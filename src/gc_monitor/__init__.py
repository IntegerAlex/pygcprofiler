"""
pygcprofiler - Python Garbage Collection Profiling Tool
Copyright (C) 2024  Akshat Kotpalliwar alias IntegerAlex

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

See Python's garbage collector in action without getting in its way.

Zero Runtime Overhead Design:
- Callback only records timestamps and counters (no I/O, no memory checks)
- Uses time.perf_counter() for high-precision, low-overhead timing
- All output is buffered and written only at shutdown
- No gc.get_objects() or memory measurement during runtime

Example usage:
    # CLI
    $ pygcprofiler run your_script.py
    $ gc-monitor run -m uvicorn main:app

    # Programmatic
    from gc_monitor import GCMonitor
    
    monitor = GCMonitor(alert_threshold_ms=100.0)
    # ... your application code ...
    monitor.stop_monitoring()
"""

__version__ = "0.4.1"
__author__ = "Akshat Kotpalliwar alias IntegerAlex"
__license__ = "LGPL-2.1-only"

from .monitor import GCMonitor
from .stats import GCStatistics
from .logging import GCLogger

__all__ = [
    "GCMonitor",
    "GCStatistics", 
    "GCLogger",
    "__version__",
]
