# SPDX-License-Identifier: LGPL-2.1-only
# Copyright (C) 2024 Akshat Kotpalliwar
"""Header templates for different application types."""

from ..detector import AppType

HEADERS = {
    AppType.WEB_ASYNC: """
🔧 PYTHON GC OPTIMIZATION FOR ASYNC WEB APPLICATION

I'm running an async web application ({framework} on {server}) experiencing GC-related 
performance issues. In async applications, GC pauses block the event loop and affect 
ALL concurrent requests simultaneously.
""",

    AppType.WEB_SYNC: """
🔧 PYTHON GC OPTIMIZATION FOR SYNC WEB APPLICATION

I'm running a synchronous web application ({framework} on {server}) with GC performance 
issues. Each worker process handles requests independently, but GC pauses still cause 
per-request latency spikes.
""",

    AppType.WEB_DJANGO: """
🔧 PYTHON GC OPTIMIZATION FOR DJANGO APPLICATION

I'm running a Django application ({server}) with GC-related performance issues. 
Django's ORM and middleware create many short-lived objects that can trigger 
frequent garbage collection.
""",

    AppType.CELERY_WORKER: """
🔧 PYTHON GC OPTIMIZATION FOR TASK WORKER

I'm running a Celery/task worker experiencing GC issues. Task workers can tolerate 
GC between tasks, but pauses during task execution affect job latency and throughput.
""",

    AppType.DATA_PROCESSING: """
🔧 PYTHON GC OPTIMIZATION FOR DATA PROCESSING

I'm running a data processing application (using {modules}) with GC issues. 
Large DataFrame/array operations create temporary objects that can trigger 
expensive Gen 2 collections.
""",

    AppType.ML_TRAINING: """
🔧 PYTHON GC OPTIMIZATION FOR ML TRAINING

I'm running ML training (using {modules}) with GC performance issues. 
Large tensor allocations and model operations can cause significant GC overhead, 
especially during batch processing.
""",

    AppType.CLI_TOOL: """
🔧 PYTHON GC OPTIMIZATION FOR CLI APPLICATION

I'm running a Python CLI tool/script with GC performance issues. 
The application processes data and exits, so startup overhead matters less 
than runtime efficiency.
""",

    AppType.ASYNC_SERVICE: """
🔧 PYTHON GC OPTIMIZATION FOR ASYNC SERVICE

I'm running an async service (using asyncio) with GC issues. 
GC pauses block the event loop and can cause timeouts in connected clients.
""",

    AppType.TESTING: """
🔧 PYTHON GC ANALYSIS FOR TEST SUITE

I'm analyzing GC behavior in a test suite. This data helps identify 
memory-intensive tests and potential leaks in the tested code.
""",

    AppType.UNKNOWN: """
🔧 PYTHON GC PERFORMANCE OPTIMIZATION

I'm experiencing GC performance issues in a Python application. 
Please provide optimization strategies based on the metrics below.
""",
}

