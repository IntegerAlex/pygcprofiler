# SPDX-License-Identifier: LGPL-2.1-only
# Copyright (C) 2024 Akshat Kotpalliwar
"""
Application type detection for context-aware prompt generation.

Detects the type of application being profiled based on:
- Imported modules (at shutdown)
- Environment variables
- Runtime characteristics
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import List, Set


class AppType(Enum):
    """Detected application type."""
    UNKNOWN = auto()
    WEB_ASYNC = auto()       # FastAPI, Starlette, aiohttp
    WEB_SYNC = auto()        # Flask, Django (sync mode)
    WEB_DJANGO = auto()      # Django specifically
    WEB_WSGI = auto()        # Gunicorn, uWSGI
    CLI_TOOL = auto()        # Command-line scripts
    DATA_PROCESSING = auto()  # Pandas, NumPy heavy workloads
    ML_TRAINING = auto()     # PyTorch, TensorFlow training
    ASYNC_SERVICE = auto()   # asyncio-based services
    CELERY_WORKER = auto()   # Celery task workers
    TESTING = auto()         # pytest, unittest


@dataclass
class AppProfile:
    """Detected application profile with context."""
    app_type: AppType
    framework: str = ""
    server: str = ""
    async_mode: bool = False
    worker_count: int = 1
    detected_modules: Set[str] = field(default_factory=set)
    hints: List[str] = field(default_factory=list)


class AppTypeDetector:
    """Detects application type from runtime context."""

    # Module patterns for detection
    WEB_ASYNC = {'fastapi', 'starlette', 'aiohttp', 'sanic', 'quart'}
    WEB_SYNC = {'flask', 'bottle', 'pyramid', 'falcon'}
    DJANGO = {'django'}
    WSGI = {'gunicorn', 'uwsgi', 'waitress', 'gevent'}
    ASGI = {'uvicorn', 'hypercorn', 'daphne'}
    DATA = {'pandas', 'numpy', 'polars', 'dask', 'vaex'}
    ML = {'torch', 'tensorflow', 'keras', 'sklearn', 'xgboost'}
    CELERY = {'celery', 'dramatiq', 'rq'}
    TEST = {'pytest', 'unittest', 'nose', 'hypothesis'}
    ASYNC = {'asyncio', 'trio', 'anyio', 'curio'}

    def __init__(self):
        self._cached_profile: AppProfile | None = None

    def detect(self) -> AppProfile:
        """Detect application type and return profile."""
        if self._cached_profile:
            return self._cached_profile

        modules = set(sys.modules.keys())
        framework = self._detect_framework(modules)
        server = self._detect_server(modules)
        async_mode = bool(modules & (self.ASYNC | self.WEB_ASYNC | self.ASGI))
        app_type = self._determine_app_type(modules, framework)
        detected = modules & (self.WEB_ASYNC | self.WEB_SYNC | self.DJANGO |
                              self.WSGI | self.ASGI | self.DATA | self.ML | self.CELERY)
        hints = self._generate_hints(app_type, server)
        worker_count = self._detect_worker_count()

        self._cached_profile = AppProfile(
            app_type=app_type, framework=framework, server=server,
            async_mode=async_mode, worker_count=worker_count,
            detected_modules=detected, hints=hints,
        )
        return self._cached_profile

    def _detect_framework(self, modules: Set[str]) -> str:
        """Detect the primary web framework."""
        if modules & self.DJANGO:
            return "Django"
        # Map module names to proper display names
        framework_names = {
            'fastapi': 'FastAPI', 'flask': 'Flask', 'aiohttp': 'aiohttp',
            'sanic': 'Sanic', 'quart': 'Quart', 'tornado': 'Tornado',
            'starlette': 'Starlette',
        }
        for name, display in framework_names.items():
            if name in modules:
                return display
        return ""

    def _detect_server(self, modules: Set[str]) -> str:
        """Detect the WSGI/ASGI server."""
        for name in ('uvicorn', 'gunicorn', 'hypercorn', 'daphne', 'waitress'):
            if name in modules:
                return name.title()
        return ""

    def _determine_app_type(self, modules: Set[str], framework: str) -> AppType:
        """Determine the primary application type."""
        if modules & self.TEST:
            return AppType.TESTING
        if modules & self.CELERY:
            return AppType.CELERY_WORKER
        if modules & self.ML:
            return AppType.ML_TRAINING
        if modules & self.DATA:
            return AppType.DATA_PROCESSING
        if framework == "Django":
            return AppType.WEB_DJANGO
        if modules & self.WEB_ASYNC or modules & self.ASGI:
            return AppType.WEB_ASYNC
        if modules & self.WEB_SYNC or modules & self.WSGI:
            return AppType.WEB_SYNC
        if modules & self.ASYNC:
            return AppType.ASYNC_SERVICE
        return AppType.CLI_TOOL

    def _generate_hints(self, app_type: AppType, server: str) -> List[str]:
        """Generate optimization hints based on detection."""
        hints = []
        hint_map = {
            AppType.WEB_ASYNC: "Async web app: GC pauses affect all concurrent requests",
            AppType.WEB_DJANGO: "Django: Consider CONN_MAX_AGE and gc.freeze() after startup",
            AppType.CELERY_WORKER: "Task worker: GC between tasks is acceptable, avoid during",
            AppType.ML_TRAINING: "ML training: Large tensor allocations may trigger Gen 2 GC",
            AppType.DATA_PROCESSING: "Data processing: Consider gc.disable() during batch ops",
        }
        if hint := hint_map.get(app_type):
            hints.append(hint)
        server_hints = {
            "Gunicorn": "Gunicorn: Apply gc.freeze() in post_fork hook",
            "Uvicorn": "Uvicorn: Use lifespan events for GC optimization",
        }
        if hint := server_hints.get(server):
            hints.append(hint)
        return hints

    def _detect_worker_count(self) -> int:
        """Detect worker count from environment."""
        for env_var in ('GUNICORN_WORKERS', 'WEB_CONCURRENCY'):
            if workers := os.environ.get(env_var):
                try:
                    return int(workers)
                except ValueError:
                    pass
        return 1
