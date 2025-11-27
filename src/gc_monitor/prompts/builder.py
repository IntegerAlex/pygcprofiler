# SPDX-License-Identifier: LGPL-2.1-only
# Copyright (C) 2024 Akshat Kotpalliwar
"""Prompt builder that assembles context-aware prompts from templates."""
from __future__ import annotations

from typing import Any, List, Tuple

from .context import GCContext
from .detector import AppType, AppTypeDetector
from .templates import (
    HEADERS, ISSUE_TEMPLATES, METRICS_TEMPLATE,
    ROLLBACK_TEMPLATE, SOLUTIONS, VALIDATION_TEMPLATE,
)


class PromptBuilder:
    """Builds context-aware AI prompts for GC optimization."""

    def __init__(self, stats: Any, events: List[Tuple], start_time: float,
                 alert_threshold_ms: float = 50.0):
        self.stats = stats
        self.events = events
        self.start_time = start_time
        self.alert_threshold_ms = alert_threshold_ms
        self.detector = AppTypeDetector()
        self.app_profile = self.detector.detect()
        self.context = GCContext.from_stats(
            stats=stats, events=events, start_time=start_time,
            app_profile=self.app_profile, alert_threshold_ms=alert_threshold_ms,
        )

    def build(self) -> str:
        """Build the complete prompt."""
        sections = [
            self._build_header(), self._build_metrics(), self._build_issues(),
            self._build_solutions(), self._build_validation(), self._build_rollback(),
        ]
        return "\n".join(filter(None, sections))

    def build_compact(self) -> str:
        """Build a compact single-line prompt for quick use."""
        m = self.context.metrics
        issues = ", ".join(i.issue_type for i in self.context.issues) or "none"
        return (
            f"Optimize Python GC ({self.app_profile.framework or 'app'}): "
            f"{m.total_collections} collections, max {m.max_duration_ms:.1f}ms pause, "
            f"{m.gc_cpu_percent:.1f}% CPU. Issues: {issues}. "
            f"Provide gc.freeze() and threshold code."
        )

    def _build_header(self) -> str:
        """Build the header section."""
        template = HEADERS.get(self.app_profile.app_type, HEADERS[AppType.UNKNOWN])
        modules_str = ", ".join(sorted(self.app_profile.detected_modules)[:5])
        return template.format(
            framework=self.app_profile.framework or "Python app",
            server=self.app_profile.server or "standalone",
            modules=modules_str or "standard library",
        ).strip()

    def _build_metrics(self) -> str:
        """Build the metrics section."""
        m = self.context.metrics
        uncollectable = f"• Uncollectable: {m.uncollectable_count} objects" if m.uncollectable_count else ""
        return METRICS_TEMPLATE.format(
            runtime=m.runtime_seconds, total=m.total_collections,
            gen0=m.collections_by_gen.get(0, 0), gen1=m.collections_by_gen.get(1, 0),
            gen2=m.collections_by_gen.get(2, 0), max_pause=m.max_duration_ms,
            avg_pause=m.avg_duration_ms, cpu_percent=m.gc_cpu_percent,
            thresholds=m.current_thresholds, counts=m.current_counts,
            uncollectable_line=uncollectable,
        ).strip()

    def _build_issues(self) -> str:
        """Build the issues section."""
        if not self.context.issues:
            return "✅ NO SIGNIFICANT GC ISSUES DETECTED\n\nGC behavior appears healthy."
        lines = ["🚨 DETECTED ISSUES:\n"]
        for issue in self.context.issues:
            template = ISSUE_TEMPLATES.get(issue.issue_type, "")
            if template:
                lines.append(template.format(metric=issue.metric, impact=issue.impact))
            else:
                lines.append(f"• [{issue.severity.upper()}] {issue.issue_type}: {issue.metric}")
        if self.app_profile.hints:
            lines.append("\n💡 APP-SPECIFIC NOTES:")
            lines.extend(f"   • {hint}" for hint in self.app_profile.hints)
        return "\n".join(lines)

    def _build_solutions(self) -> str:
        """Build the solutions section with framework-specific code."""
        t0, t1, t2 = self._calculate_thresholds()
        template = SOLUTIONS.get(self._get_solution_key(), SOLUTIONS['generic'])
        return template.format(threshold0=t0, threshold1=t1, threshold2=t2).strip()

    def _build_validation(self) -> str:
        """Build the validation section."""
        m = self.context.metrics
        if m.gc_cpu_percent > 5:
            expected = f"~{m.gc_cpu_percent * 0.7:.0f}% reduction in GC CPU overhead"
        elif m.max_duration_ms > 100:
            expected = f"Max pause reduction from {m.max_duration_ms:.0f}ms to <50ms"
        elif m.collections_by_gen.get(2, 0) > 0:
            expected = "Elimination of most Gen 2 collections after startup"
        else:
            expected = "Reduced collection frequency and more predictable latency"
        return VALIDATION_TEMPLATE.format(expected_improvement=expected).strip()

    def _build_rollback(self) -> str:
        """Build the rollback section."""
        return ROLLBACK_TEMPLATE.strip()

    def _calculate_thresholds(self) -> Tuple[int, int, int]:
        """Calculate recommended GC thresholds based on metrics."""
        m = self.context.metrics
        if m.gc_cpu_percent > 5 or m.max_duration_ms > 100:
            return (50000, 10, 10)  # Aggressive
        if m.gc_cpu_percent > 2 or m.max_duration_ms > 50:
            return (25000, 10, 10)  # Moderate
        if m.collections_by_gen.get(0, 0) > 1000:
            return (10000, 10, 10)  # Many Gen 0
        return (5000, 10, 10)  # Conservative

    def _get_solution_key(self) -> str:
        """Get the appropriate solution template key."""
        server = self.app_profile.server.lower()
        framework = self.app_profile.framework.lower()
        app_type = self.app_profile.app_type
        if 'uvicorn' in server or 'hypercorn' in server:
            return 'uvicorn'
        if 'gunicorn' in server:
            return 'gunicorn'
        if 'django' in framework or app_type == AppType.WEB_DJANGO:
            return 'django'
        if app_type == AppType.CELERY_WORKER:
            return 'celery'
        if app_type == AppType.DATA_PROCESSING:
            return 'data_processing'
        return 'generic'
