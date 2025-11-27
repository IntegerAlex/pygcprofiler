# SPDX-License-Identifier: LGPL-2.1-only
# Copyright (C) 2024 Akshat Kotpalliwar
"""Framework-specific solution templates."""

SOLUTIONS = {
    'generic': """
🔧 RECOMMENDED OPTIMIZATIONS:

```python
import gc

# 1. After application startup/initialization:
gc.collect(2)  # Full collection
gc.freeze()    # Freeze all current objects (Python 3.7+)

# 2. Tune thresholds based on your workload:
gc.set_threshold({threshold0}, {threshold1}, {threshold2})

# 3. Verify optimization:
print(f"Frozen: {{gc.get_freeze_count()}} objects")
print(f"Thresholds: {{gc.get_threshold()}}")
```
""",

    'uvicorn': """
🔧 UVICORN-SPECIFIC OPTIMIZATION:

```python
# In your FastAPI/Starlette app:
from contextlib import asynccontextmanager
import gc

@asynccontextmanager
async def lifespan(app):
    # Startup: freeze after all imports/init
    gc.collect(2)
    gc.freeze()
    gc.set_threshold({threshold0}, {threshold1}, {threshold2})
    print(f"GC optimized: {{gc.get_freeze_count()}} frozen")
    yield
    # Shutdown: nothing needed

app = FastAPI(lifespan=lifespan)
```
""",

    'gunicorn': """
🔧 GUNICORN-SPECIFIC OPTIMIZATION:

```python
# In gunicorn.conf.py:
import gc

def post_fork(server, worker):
    '''Called after worker fork - optimize GC per worker.'''
    gc.collect(2)
    gc.freeze()
    gc.set_threshold({threshold0}, {threshold1}, {threshold2})
    server.log.info(f"Worker {{worker.pid}}: GC optimized")

# Or in your WSGI app's startup:
gc.collect(2)
gc.freeze()
gc.set_threshold({threshold0}, {threshold1}, {threshold2})
```
""",

    'django': """
🔧 DJANGO-SPECIFIC OPTIMIZATION:

```python
# In your settings.py or wsgi.py:
import gc

# After Django is fully loaded:
gc.collect(2)
gc.freeze()
gc.set_threshold({threshold0}, {threshold1}, {threshold2})

# Also consider in settings.py:
CONN_MAX_AGE = 600  # Reuse DB connections
```
""",

    'celery': """
🔧 CELERY-SPECIFIC OPTIMIZATION:

```python
# In your celery app configuration:
from celery.signals import worker_process_init
import gc

@worker_process_init.connect
def optimize_gc(**kwargs):
    gc.collect(2)
    gc.freeze()
    gc.set_threshold({threshold0}, {threshold1}, {threshold2})
    
# For long-running tasks, consider:
@app.task
def my_task():
    gc.disable()  # Disable during task
    try:
        # ... task work ...
        pass
    finally:
        gc.enable()
        gc.collect(0)  # Quick collection after
```
""",

    'data_processing': """
🔧 DATA PROCESSING OPTIMIZATION:

```python
import gc

# For batch processing:
gc.disable()  # Disable during heavy computation

for batch in data_batches:
    process(batch)
    # Optional: manual collection between batches
    # gc.collect(0)

gc.enable()
gc.collect(2)  # Full collection after

# For pandas/numpy:
# - Use inplace=True where possible
# - Delete intermediate DataFrames explicitly
# - Consider chunked processing
```
""",
}

