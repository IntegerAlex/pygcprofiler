# SPDX-License-Identifier: LGPL-2.1-only
# Copyright (C) 2024 Akshat Kotpalliwar

"""
Process memory utilities for pygcprofiler
"""

import gc
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


def estimate_memory_usage(stats_only: bool) -> int:
    """
    Estimate current process memory usage.

    Falls back to counting tracked GC objects if psutil is unavailable or
    in "stats only" mode.
    """
    if stats_only:
        return len(gc.get_objects()) * 64

    rss = _psutil_rss()
    if rss:
        return rss
    return len(gc.get_objects()) * 64

