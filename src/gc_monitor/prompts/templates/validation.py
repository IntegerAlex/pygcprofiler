# SPDX-License-Identifier: LGPL-2.1-only
# Copyright (C) 2024 Akshat Kotpalliwar
"""Validation and rollback templates."""

VALIDATION_TEMPLATE = """
✅ VALIDATION STEPS:

1. Before optimization, record baseline:
   - p50, p95, p99 latency
   - Request throughput
   - Memory usage pattern

2. After applying changes:
   - Run: `pygcprofiler run --stats-only your_app.py`
   - Compare GC metrics
   - Monitor for 24h in production

3. Expected improvements:
   - {expected_improvement}
   - Reduced p99 latency variance
   - More predictable response times
"""

ROLLBACK_TEMPLATE = """
⚠️ ROLLBACK PLAN:

If issues occur after optimization:

```python
import gc

# Reset to defaults:
gc.unfreeze()  # Python 3.7+
gc.set_threshold(700, 10, 10)  # CPython defaults
gc.enable()
```

Monitor for: increased memory usage, slower response times, OOM errors.
"""

