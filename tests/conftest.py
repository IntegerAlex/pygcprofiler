# SPDX-License-Identifier: LGPL-2.1-only
# Copyright (C) 2024 Akshat Kotpalliwar
"""Pytest configuration and fixtures."""

import gc
import sys
import pytest
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


@pytest.fixture
def clean_gc_state():
    """Ensure clean GC state before and after tests."""
    # Store original callbacks
    original_callbacks = list(gc.callbacks)
    original_debug = gc.get_debug()
    
    yield
    
    # Restore original state
    gc.callbacks.clear()
    gc.callbacks.extend(original_callbacks)
    gc.set_debug(original_debug)


@pytest.fixture
def sample_script(tmp_path):
    """Create a sample Python script for testing."""
    script = tmp_path / "sample.py"
    script.write_text("""
import gc

# Force some GC activity
objects = []
for i in range(1000):
    objects.append([i] * 100)
    if i % 100 == 0:
        objects.clear()

print("Sample script completed")
""")
    return script


@pytest.fixture
def long_running_script(tmp_path):
    """Create a script that runs for a bit longer."""
    script = tmp_path / "long_running.py"
    script.write_text("""
import time
import gc

# Simulate some work with GC activity
for _ in range(5):
    data = [list(range(1000)) for _ in range(100)]
    time.sleep(0.1)
    del data
    gc.collect()

print("Long running script completed")
""")
    return script

