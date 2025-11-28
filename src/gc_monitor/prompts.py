"""
AI prompt generation for GC optimization recommendations
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
from typing import Any, Dict, List

from .stats import GCStatistics
from .blunders import detect_gc_blunders


class PromptBuilder:
    """
    Builds comprehensive AI prompts for GC optimization based on monitoring data.
    
    Generates detailed prompts that can be used with AI assistants to get
    expert recommendations for optimizing garbage collection performance.
    """
    
    def __init__(
        self,
        stats: GCStatistics,
        events: List[tuple],
        start_time: float,
        alert_threshold_ms: float = 50.0,
    ):
        """
        Initialize the prompt builder.
        
        Args:
            stats: GCStatistics object with collected statistics
            events: List of GC event tuples (relative_time, generation, duration_ms, collected, uncollectable)
            start_time: Start time of monitoring
            alert_threshold_ms: Alert threshold in milliseconds
        """
        self.stats = stats
        self.events = events
        self.start_time = start_time
        self.alert_threshold_ms = alert_threshold_ms
    
    def _format_duration(self, duration_ms: float) -> str:
        """Format duration in human-readable format."""
        if duration_ms < 1:
            return f"{duration_ms:.3f}ms"
        elif duration_ms < 1000:
            return f"{duration_ms:.1f}ms"
        else:
            return f"{duration_ms/1000:.2f}s"
    
    def _get_runtime_stats(self) -> Dict[str, Any]:
        """Calculate runtime statistics."""
        runtime = max(time.time() - self.start_time, 1)
        totals = self.stats.stats
        
        avg_duration = 0.0
        if totals['total_collections'] > 0:
            avg_duration = totals['total_duration_ms'] / totals['total_collections']
        
        gc_cpu_percent = (totals['total_duration_ms'] / 1000) / runtime * 100
        
        return {
            'runtime_seconds': runtime,
            'total_collections': totals['total_collections'],
            'total_duration_ms': totals['total_duration_ms'],
            'avg_duration_ms': avg_duration,
            'max_duration_ms': totals['max_duration_ms'],
            'gc_cpu_percent': gc_cpu_percent,
            'collections_by_generation': dict(totals['collections_by_generation']),
        }
    
    def _get_percentiles(self, generation: int) -> Dict[str, float]:
        """Calculate percentiles for a specific generation."""
        samples = list(self.stats.duration_history[generation])
        if not samples:
            return {}
        
        sorted_samples = sorted(samples)
        n = len(sorted_samples)
        
        def percentile(p: float) -> float:
            if n == 1:
                return sorted_samples[0]
            k = (n - 1) * (p / 100.0)
            lower = int(k)
            upper = min(int(k) + 1, n - 1)
            if lower == upper:
                return sorted_samples[int(k)]
            return sorted_samples[lower] + (sorted_samples[upper] - sorted_samples[lower]) * (k - lower)
        
        return {
            'p50': percentile(50),
            'p75': percentile(75),
            'p90': percentile(90),
            'p95': percentile(95),
            'p99': percentile(99),
        }
    
    def _convert_events_to_dicts(self) -> List[Dict[str, Any]]:
        """Convert event tuples to dictionaries for blunder detection."""
        event_dicts = []
        for event in self.events:
            relative_time, generation, duration_ms, collected, uncollectable = event
            event_dicts.append({
                'generation': generation,
                'duration_ms': duration_ms,
                'collected': collected,
                'uncollectable': uncollectable,
            })
        return event_dicts
    
    def build(self) -> str:
        """
        Build a comprehensive AI optimization prompt.
        
        Returns:
            A formatted string prompt ready to use with an AI assistant
        """
        runtime_stats = self._get_runtime_stats()
        event_dicts = self._convert_events_to_dicts()
        blunders, recommendations = detect_gc_blunders(self.stats, event_dicts, self.start_time)
        
        prompt_parts = []
        
        # Header
        prompt_parts.append("=" * 80)
        prompt_parts.append("PYTHON GARBAGE COLLECTION OPTIMIZATION REQUEST")
        prompt_parts.append("=" * 80)
        prompt_parts.append("")
        prompt_parts.append("I need expert help optimizing garbage collection performance in my Python application.")
        prompt_parts.append("")
        
        # Runtime Statistics
        prompt_parts.append("## Runtime Statistics")
        prompt_parts.append(f"- **Total Runtime**: {runtime_stats['runtime_seconds']:.1f} seconds")
        prompt_parts.append(f"- **Total GC Collections**: {runtime_stats['total_collections']}")
        prompt_parts.append(f"- **Total GC Time**: {self._format_duration(runtime_stats['total_duration_ms'])}")
        prompt_parts.append(f"- **Average GC Duration**: {self._format_duration(runtime_stats['avg_duration_ms'])}")
        prompt_parts.append(f"- **Maximum GC Duration**: {self._format_duration(runtime_stats['max_duration_ms'])}")
        prompt_parts.append(f"- **GC CPU Usage**: {runtime_stats['gc_cpu_percent']:.2f}% of total runtime")
        prompt_parts.append(f"- **Alert Threshold**: {self.alert_threshold_ms}ms")
        prompt_parts.append("")
        
        # Collections by Generation
        prompt_parts.append("## Collections by Generation")
        for gen in sorted(runtime_stats['collections_by_generation'].keys()):
            count = runtime_stats['collections_by_generation'][gen]
            percentiles = self._get_percentiles(gen)
            prompt_parts.append(f"**Generation {gen}**:")
            prompt_parts.append(f"  - Collections: {count}")
            if percentiles:
                prompt_parts.append(f"  - P50: {self._format_duration(percentiles['p50'])}")
                prompt_parts.append(f"  - P95: {self._format_duration(percentiles['p95'])}")
                prompt_parts.append(f"  - P99: {self._format_duration(percentiles['p99'])}")
        prompt_parts.append("")
        
        # Detected Blunders
        if blunders:
            prompt_parts.append("## Detected Performance Issues")
            for i, blunder in enumerate(blunders, 1):
                prompt_parts.append(f"### Issue {i}: {blunder['type'].replace('_', ' ').title()}")
                prompt_parts.append(f"- **Severity**: {blunder['severity'].upper()}")
                prompt_parts.append(f"- **Metric**: {blunder['metric']}")
                prompt_parts.append(f"- **Impact**: {blunder['impact']}")
                prompt_parts.append("")
        
        # Recommendations
        if recommendations:
            prompt_parts.append("## Current Recommendations")
            for i, rec in enumerate(recommendations, 1):
                prompt_parts.append(f"{i}. {rec}")
            prompt_parts.append("")
        
        # Request for AI assistance
        prompt_parts.append("## Request")
        prompt_parts.append("Based on this GC monitoring data, please provide:")
        prompt_parts.append("")
        prompt_parts.append("1. **Root Cause Analysis**: What patterns or code structures are likely causing these GC issues?")
        prompt_parts.append("")
        prompt_parts.append("2. **Specific Code Recommendations**: Concrete, actionable code changes I can make to reduce GC pressure.")
        prompt_parts.append("")
        prompt_parts.append("3. **GC Configuration Tuning**: Specific `gc.set_threshold()` values or other GC settings to try.")
        prompt_parts.append("")
        prompt_parts.append("4. **Architecture Suggestions**: High-level design changes that could reduce object allocation pressure.")
        prompt_parts.append("")
        prompt_parts.append("5. **Monitoring Strategy**: What additional metrics or monitoring would help diagnose further issues?")
        prompt_parts.append("")
        prompt_parts.append("Please prioritize recommendations that will have the highest impact on reducing GC pause times and CPU usage.")
        prompt_parts.append("")
        prompt_parts.append("=" * 80)
        
        return "\n".join(prompt_parts)


