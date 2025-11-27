# SPDX-License-Identifier: LGPL-2.1-only
# Copyright (C) 2024 Akshat Kotpalliwar
"""
Modular AI prompt generation system for pygcprofiler.

This package provides dynamic, context-aware prompt generation based on:
- Application type (web server, CLI, async, data processing, etc.)
- Detected GC issues and their severity
- Runtime metrics and thresholds
- Framework-specific optimizations

Usage:
    from gc_monitor.prompts import PromptBuilder
    
    builder = PromptBuilder(stats, events, start_time)
    prompt = builder.build()
"""

from .builder import PromptBuilder
from .detector import AppTypeDetector, AppType
from .context import GCContext

__all__ = [
    "PromptBuilder",
    "AppTypeDetector",
    "AppType",
    "GCContext",
]

