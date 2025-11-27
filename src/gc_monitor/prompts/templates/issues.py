# SPDX-License-Identifier: LGPL-2.1-only
# Copyright (C) 2024 Akshat Kotpalliwar
"""Issue-specific templates and metrics template."""

# Metrics display template
METRICS_TEMPLATE = """
📊 GC METRICS (collected over {runtime:.1f}s):

• Collections: {total} total ({gen0} Gen0, {gen1} Gen1, {gen2} Gen2)
• Pauses: max {max_pause:.1f}ms, avg {avg_pause:.1f}ms
• CPU: {cpu_percent:.1f}% spent on GC
• Thresholds: {thresholds}
• Object counts: {counts}
{uncollectable_line}
"""

# Issue-specific templates
ISSUE_TEMPLATES = {
    'excessive_gen2': """
⚠️ EXCESSIVE GEN 2 COLLECTIONS
   Metric: {metric}
   Impact: {impact}
   
   Gen 2 collections scan ALL tracked objects and cause the longest pauses.
   This often happens when startup objects aren't frozen.
""",

    'long_pauses': """
🚨 LONG GC PAUSES DETECTED
   Metric: {metric}
   Impact: {impact}
   
   Pauses over 50ms are user-visible. Over 100ms causes poor UX.
   This affects p99 latency significantly.
""",

    'high_cpu': """
💸 HIGH GC CPU OVERHEAD
   Metric: {metric}
   Impact: {impact}
   
   You're paying for CPU cycles spent on garbage collection.
   This directly impacts cloud costs and throughput.
""",

    'uncollectable': """
🔴 MEMORY LEAK DETECTED
   Metric: {metric}
   Impact: {impact}
   
   Uncollectable objects indicate reference cycles that prevent cleanup.
   Memory usage will grow over time.
""",

    'frequent_gen0': """
⚡ VERY FREQUENT GEN 0 COLLECTIONS
   Metric: {metric}
   Impact: {impact}
   
   While Gen 0 is fast, very frequent collections add up.
   Consider batching allocations or increasing threshold.
""",
}

