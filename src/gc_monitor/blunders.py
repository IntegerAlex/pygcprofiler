"""
GC blunder detection utilities for pygcprofiler
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
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Tuple

from .stats import GCStatistics


Blunder = Dict[str, Any]


def detect_gc_blunders(
    stats: GCStatistics,
    gc_events: List[Dict[str, Any]],
    start_time: float,
) -> Tuple[List[Blunder], List[str]]:
    """Detect common GC issues and produce recommendations."""
    blunders: List[Blunder] = []
    recommendations: List[str] = []
    totals = stats.stats

    total_collections = totals["total_collections"]
    gen2_collections = totals["collections_by_generation"].get(2, 0)
    if total_collections and gen2_collections / total_collections > 0.1:
        blunders.append(
            {
                "type": "excessive_gen2_collections",
                "severity": "high",
                "metric": f"{gen2_collections} Gen 2 collections out of {total_collections} total",
                "impact": "Causes long application pauses and high latency spikes",
            }
        )
        recommendations.append(
            "Consider using gc.freeze() after application initialization to move startup objects to permanent generation"
        )

    if totals["max_duration_ms"] > 50:
        severity = "critical" if totals["max_duration_ms"] > 100 else "high"
        blunders.append(
            {
                "type": "long_gc_pauses",
                "severity": severity,
                "metric": f"Maximum GC pause: {totals['max_duration_ms']:.1f}ms",
                "impact": "Causes user-visible latency spikes and poor application responsiveness",
            }
        )
        recommendations.append(
            "Increase GC thresholds dramatically (e.g., from default 700 to 50,000) to reduce collection frequency"
        )

    runtime = max(time.time() - start_time, 1)
    gc_cpu_percent = (totals["total_duration_ms"] / 1000) / runtime * 100
    if gc_cpu_percent > 2:
        severity = "critical" if gc_cpu_percent > 5 else "high"
        blunders.append(
            {
                "type": "high_gc_cpu_usage",
                "severity": severity,
                "metric": f"GC uses {gc_cpu_percent:.1f}% of total CPU time",
                "impact": f"Represents approximately {gc_cpu_percent/0.35:.1f}% of allocated cloud resources wasted on garbage collection",
            }
        )
        recommendations.append("Combine gc.freeze() with threshold tuning for optimal performance")

    total_uncollectable = sum(event.get("uncollectable", 0) for event in gc_events)
    if total_uncollectable > 100:
        blunders.append(
            {
                "type": "uncollectable_objects",
                "severity": "medium",
                "metric": f"{total_uncollectable} uncollectable objects found",
                "impact": "Memory leaks and inefficient memory usage",
            }
        )
        recommendations.append("Investigate reference cycles and consider using weak references or manual cleanup")

    return blunders, recommendations

