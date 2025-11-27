# SPDX-License-Identifier: LGPL-2.1-only
# Copyright (C) 2024 Akshat Kotpalliwar
"""
GC context and metrics collection for prompt generation.

Collects and organizes GC metrics, issues, and runtime context
for use in prompt templates.
"""

from __future__ import annotations

import gc
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

from .detector import AppProfile, AppType


@dataclass
class GCMetrics:
    """Collected GC metrics."""
    total_collections: int = 0
    total_duration_ms: float = 0.0
    max_duration_ms: float = 0.0
    avg_duration_ms: float = 0.0
    collections_by_gen: Dict[int, int] = field(default_factory=dict)
    gc_cpu_percent: float = 0.0
    runtime_seconds: float = 0.0
    current_thresholds: Tuple[int, int, int] = (700, 10, 10)
    current_counts: Tuple[int, int, int] = (0, 0, 0)
    uncollectable_count: int = 0


@dataclass
class GCIssue:
    """A detected GC issue."""
    issue_type: str
    severity: str  # 'critical', 'high', 'medium', 'low'
    metric: str
    impact: str
    recommendation: str


@dataclass
class GCContext:
    """Complete GC context for prompt generation."""
    metrics: GCMetrics
    issues: List[GCIssue]
    app_profile: AppProfile
    slow_locations: List[str] = field(default_factory=list)

    @classmethod
    def from_stats(
        cls,
        stats: Any,  # GCStatistics
        events: List[Tuple],
        start_time: float,
        app_profile: AppProfile,
        alert_threshold_ms: float = 50.0,
    ) -> "GCContext":
        """Build context from statistics and events."""
        runtime = max(time.time() - start_time, 1)
        totals = stats.stats

        # Calculate metrics
        total_collections = totals['total_collections']
        total_duration = totals['total_duration_ms']
        max_duration = totals['max_duration_ms']
        avg_duration = total_duration / total_collections if total_collections > 0 else 0

        # Uncollectable count from events (tuple index 4)
        uncollectable = sum(e[4] for e in events) if events else 0

        metrics = GCMetrics(
            total_collections=total_collections,
            total_duration_ms=total_duration,
            max_duration_ms=max_duration,
            avg_duration_ms=avg_duration,
            collections_by_gen=dict(totals['collections_by_generation']),
            gc_cpu_percent=(total_duration / 1000) / runtime * 100,
            runtime_seconds=runtime,
            current_thresholds=gc.get_threshold(),
            current_counts=gc.get_count(),
            uncollectable_count=uncollectable,
        )

        # Detect issues
        issues = cls._detect_issues(metrics, alert_threshold_ms)

        # Extract slow locations (if available in events)
        slow_locations: List[str] = []

        return cls(
            metrics=metrics,
            issues=issues,
            app_profile=app_profile,
            slow_locations=slow_locations,
        )

    @staticmethod
    def _detect_issues(metrics: GCMetrics, alert_threshold_ms: float) -> List[GCIssue]:
        """Detect GC issues from metrics."""
        issues = []

        # Issue: Excessive Gen 2 collections
        gen2 = metrics.collections_by_gen.get(2, 0)
        total = metrics.total_collections
        if total > 0 and gen2 / total > 0.1:
            issues.append(GCIssue(
                issue_type='excessive_gen2',
                severity='high',
                metric=f"{gen2} Gen 2 collections ({gen2/total*100:.0f}% of total)",
                impact='Long application pauses, latency spikes',
                recommendation='Use gc.freeze() after initialization',
            ))

        # Issue: Long GC pauses
        if metrics.max_duration_ms > alert_threshold_ms:
            severity = 'critical' if metrics.max_duration_ms > 100 else 'high'
            issues.append(GCIssue(
                issue_type='long_pauses',
                severity=severity,
                metric=f"Max pause: {metrics.max_duration_ms:.1f}ms",
                impact='User-visible latency, poor responsiveness',
                recommendation='Increase GC thresholds (e.g., 50000, 10, 10)',
            ))

        # Issue: High GC CPU usage
        if metrics.gc_cpu_percent > 2:
            severity = 'critical' if metrics.gc_cpu_percent > 5 else 'high'
            issues.append(GCIssue(
                issue_type='high_cpu',
                severity=severity,
                metric=f"GC uses {metrics.gc_cpu_percent:.1f}% CPU",
                impact=f"~{metrics.gc_cpu_percent/0.35:.0f}% cloud cost on GC",
                recommendation='Combine gc.freeze() with threshold tuning',
            ))

        # Issue: Uncollectable objects
        if metrics.uncollectable_count > 100:
            issues.append(GCIssue(
                issue_type='uncollectable',
                severity='medium',
                metric=f"{metrics.uncollectable_count} uncollectable objects",
                impact='Memory leaks, growing memory usage',
                recommendation='Check for reference cycles, use weakref',
            ))

        # Issue: Very frequent Gen 0 collections
        gen0 = metrics.collections_by_gen.get(0, 0)
        per_second = gen0 / metrics.runtime_seconds if metrics.runtime_seconds > 0 else 0
        if per_second > 10:
            issues.append(GCIssue(
                issue_type='frequent_gen0',
                severity='medium',
                metric=f"{per_second:.0f} Gen 0 collections/second",
                impact='Overhead from frequent small collections',
                recommendation='Increase Gen 0 threshold or batch allocations',
            ))

        return issues

    def get_severity_summary(self) -> str:
        """Get a summary of issue severities."""
        if not self.issues:
            return "healthy"
        
        severities = [i.severity for i in self.issues]
        if 'critical' in severities:
            return "critical"
        if 'high' in severities:
            return "needs_attention"
        return "minor_issues"

