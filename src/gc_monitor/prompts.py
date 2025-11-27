"""
AI prompt generation helpers for pygcprofiler
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

import gc
import time
from typing import Any, Dict, List

from .stats import GCStatistics


def build_ai_prompt(
    stats: GCStatistics,
    gc_events: List[Dict[str, Any]],
    blunders: List[Dict[str, Any]],
    recommendations: List[str],
    start_time: float,
) -> str:
    """Construct a concise optimization prompt for AI copilots."""
    totals = stats.stats
    runtime = max(time.time() - start_time, 1)
    current_thresholds = gc.get_threshold()
    cpu_usage = (totals['total_duration_ms']/1000)/runtime*100
    
    # Find slow GC events with locations
    slow_events = [e for e in gc_events if e.get('duration_ms', 0) >= 10 and 'location' in e]
    locations = []
    if slow_events:
        # Get unique locations from slowest events
        sorted_events = sorted(slow_events, key=lambda x: x.get('duration_ms', 0), reverse=True)
        seen_locs = set()
        for event in sorted_events[:3]:  # Top 3 locations
            loc = event.get('location', '')
            if loc and loc not in seen_locs:
                locations.append(loc)
                seen_locs.add(loc)
    
    loc_text = f" Slow GC at: {', '.join(locations)}." if locations else ""
    
    prompt = (
        f"Optimize Python GC: {totals['total_collections']} collections over {runtime:.1f}s, "
        f"max pause {totals['max_duration_ms']:.1f}ms, {cpu_usage:.1f}% CPU, thresholds {current_thresholds}.{loc_text} "
        f"Provide gc.freeze() and threshold tuning code with specific values, expected impact, and validation."
    )
    
    return prompt

