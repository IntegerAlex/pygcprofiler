# SPDX-License-Identifier: LGPL-2.1-only
# Copyright (C) 2024 Akshat Kotpalliwar
"""
AI prompt generation helpers for pygcprofiler.

This module provides backward-compatible functions that delegate
to the new modular prompt system in gc_monitor.prompts package.
"""

from __future__ import annotations

from typing import Any, Dict, List

from .prompts import PromptBuilder
from .stats import GCStatistics


def build_ai_prompt(
    stats: GCStatistics,
    gc_events: List[Dict[str, Any]],
    blunders: List[Dict[str, Any]],
    recommendations: List[str],
    start_time: float,
) -> str:
    """
    Construct a concise optimization prompt for AI copilots.
    
    This is a backward-compatible wrapper around the new PromptBuilder.
    For more control, use PromptBuilder directly.
    """
    # Convert dict events to tuples if needed (for compatibility)
    tuple_events = []
    for e in gc_events:
        if isinstance(e, dict):
            tuple_events.append((
                e.get('timestamp', 0) - start_time,
                e.get('generation', 0),
                e.get('duration_ms', 0),
                e.get('collected', 0),
                e.get('uncollectable', 0),
            ))
        else:
            tuple_events.append(e)

    builder = PromptBuilder(
        stats=stats,
        events=tuple_events,
        start_time=start_time,
    )

    # Return compact prompt for backward compatibility
    return builder.build_compact()


def build_full_prompt(
    stats: GCStatistics,
    events: List,
    start_time: float,
    alert_threshold_ms: float = 50.0,
) -> str:
    """
    Build a comprehensive AI prompt with full context.
    
    This is the recommended function for generating detailed prompts.
    """
    builder = PromptBuilder(
        stats=stats,
        events=events,
        start_time=start_time,
        alert_threshold_ms=alert_threshold_ms,
    )
    return builder.build()
