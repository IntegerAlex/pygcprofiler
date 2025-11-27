# SPDX-License-Identifier: LGPL-2.1-only
# Copyright (C) 2024 Akshat Kotpalliwar

"""
AI prompt generation helpers
"""

from __future__ import annotations

import gc
import time
from textwrap import dedent
from typing import Any, Dict, List

from .stats import GCStatistics


def build_ai_prompt(
    stats: GCStatistics,
    gc_events: List[Dict[str, Any]],
    blunders: List[Dict[str, Any]],
    recommendations: List[str],
    start_time: float,
) -> str:
    """Construct a rich optimization prompt for AI copilots."""
    totals = stats.stats
    runtime = max(time.time() - start_time, 1)
    current_thresholds = gc.get_threshold()
    current_counts = gc.get_count()

    summary_lines = [
        "🔧 PYTHON GC PERFORMANCE OPTIMIZATION REQUEST",
        "",
        "I'm experiencing significant performance issues with Python's garbage collector in a production web application. Please provide specific, actionable optimization strategies.",
        "",
        f"📊 CURRENT GC METRICS (collected over {runtime:.1f} seconds):",
        "",
        f"• Total GC Collections: {totals['total_collections']}",
        "",
        "• Generation Breakdown:",
        f"  - Gen 0: {totals['collections_by_generation'].get(0, 0)} collections",
        f"  - Gen 1: {totals['collections_by_generation'].get(1, 0)} collections",
        f"  - Gen 2: {totals['collections_by_generation'].get(2, 0)} collections",
        "",
        "• Performance Impact:",
        f"  - Max GC Pause: {totals['max_duration_ms']:.1f}ms",
        f"  - Total GC Time: {totals['total_duration_ms']/1000:.2f}s",
        f"  - CPU Usage by GC: {(totals['total_duration_ms']/1000)/runtime*100:.1f}%",
        "",
        f"• Current GC Thresholds: {current_thresholds}",
        f"• Current Object Counts: {current_counts}",
        f"• Uncollectable Objects Found: {sum(event.get('uncollectable', 0) for event in gc_events)}",
        "",
        "🚨 DETECTED ISSUES:",
    ]

    if blunders:
        summary_lines.extend(
            f"• [{b['severity'].upper()}] {b['type'].replace('_', ' ').title()}: {b['metric']} - {b['impact']}"
            for b in blunders
        )
    else:
        summary_lines.append("• None detected during this interval.")

    summary_lines.extend(
        [
            "",
            "💡 RECOMMENDATIONS TO CONSIDER:",
        ]
    )

    if recommendations:
        summary_lines.extend(f"• {rec}" for rec in recommendations)
    else:
        summary_lines.append("• Collect more data to produce actionable insights.")

    summary_lines.extend(
        [
            "",
            "🎯 APPLICATION CONTEXT:",
            "",
            "- This is a web application (likely Django/FastAPI/Flask) handling HTTP requests",
            "- We cannot modify the core application code extensively",
            "- We need solutions that can be applied at startup/initialization",
            "- The goal is to reduce p95 latency and improve overall throughput",
            "- We're using standard CPython (not PyPy or other implementations)",
            "",
            "🔧 SPECIFIC OPTIMIZATION REQUESTS:",
            "",
            "1. Provide EXACT code snippets to place at application startup that will:",
            "   - Freeze initialization objects to prevent them from being scanned in Gen 2",
            "   - Set optimal GC thresholds based on our metrics",
            "   - Add minimal-overhead monitoring for production",
            "",
            "2. For each recommendation, explain:",
            "   - WHY it will help our specific metrics",
            "   - WHAT the expected performance improvement will be",
            "   - ANY potential risks or trade-offs",
            "   - HOW to validate the improvement",
            "",
            "3. Include production-ready monitoring code that can be integrated with OpenTelemetry or similar observability tools.",
            "4. If applicable, provide strategies to identify and fix the root causes of uncollectable objects.",
            "",
            "🚀 FORMAT REQUIREMENTS:",
            "",
            "- Provide ready-to-copy code blocks with proper error handling",
            "- Include comments explaining each optimization",
            "- Give specific threshold values based on our metrics (don't use placeholders)",
            "- Prioritize solutions that can be deployed immediately with minimal risk",
            "- Include rollback strategies if optimizations cause issues",
            "",
            "Example of the type of code we need at startup:",
            "",
            "```python",
            "import gc",
            "",
            "# Optimization 1: Clean up and freeze startup objects",
            "gc.collect(2)  # Full collection of all generations",
            "gc.freeze()    # Move all tracked objects to permanent generation",
            "",
            "# Optimization 2: Set aggressive thresholds based on our workload",
            "current_gen1, current_gen2 = gc.get_threshold()[1:]",
            "# OUR SPECIFIC THRESHOLDS BASED ON METRICS:",
            "gc.set_threshold(50000, current_gen1, current_gen2)  # Dramatically reduce collection frequency",
            "",
            'print(f"GMEM GC optimized: thresholds set to {gc.get_threshold()}, {gc.get_freeze_count()} objects frozen")',
            "```",
        ]
    )

    return dedent("\n".join(summary_lines))

