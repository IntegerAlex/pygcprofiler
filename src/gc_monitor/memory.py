"""
Process memory utilities for pygcprofiler
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

Zero Runtime Overhead Design:
- NEVER calls gc.get_objects() - this scans the entire object graph
- Uses psutil for memory measurement when available
- Returns 0 when psutil is unavailable (no fallback to expensive operations)
"""

import os
from typing import Protocol


class _MemoryProcess(Protocol):
    def memory_info(self):
        ...


def _psutil_rss() -> int:
    """Return RSS using psutil if available."""
    try:
        import psutil

        process: _MemoryProcess = psutil.Process(os.getpid())
        return process.memory_info().rss
    except Exception:  # noqa: BLE001
        return 0


def get_memory_usage() -> int:
    """
    Get current process memory usage in bytes.
    
    Returns RSS from psutil if available, otherwise returns 0.
    
    IMPORTANT: This function NEVER calls gc.get_objects() as that would
    scan the entire object graph and add significant overhead.
    """
    return _psutil_rss()


# Deprecated: kept for backwards compatibility but should not be used
def estimate_memory_usage(stats_only: bool) -> int:
    """
    Deprecated: Use get_memory_usage() instead.
    
    This function previously fell back to gc.get_objects() which violates
    zero-overhead principles. Now it simply returns psutil RSS or 0.
    """
    return _psutil_rss()
