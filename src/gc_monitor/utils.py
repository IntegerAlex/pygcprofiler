"""Utility functions for GC monitoring."""

import gc
import os
import time


def get_memory_usage():
    """Get current memory usage in bytes - ONLY called at shutdown."""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        return process.memory_info().rss
    except (ImportError, Exception):
        # Return 0 instead of calling gc.get_objects()
        # We don't want to scan the object graph even at shutdown if psutil isn't available
        return 0


def take_snapshot(monitor):
    """Take snapshot of GC state - ONLY called at shutdown."""
    if monitor.stats_only:
        return

    monitor._initialize_components()

    snapshot = {
        'timestamp': time.time(),
        'generations': {}
    }

    try:
        # gc.get_count() is cheap - just returns 3 integers
        counts = gc.get_count()
        snapshot['generations'] = {
            'gen0': counts[0] if len(counts) > 0 else 0,
            'gen1': counts[1] if len(counts) > 1 else 0,
            'gen2': counts[2] if len(counts) > 2 else 0
        }
    except Exception as e:
        snapshot['error'] = str(e)

    # Only get object count at shutdown if explicitly requested
    if monitor.dump_objects:
        snapshot['total_objects'] = len(gc.get_objects())

    if monitor.json_output:
        import json
        monitor.logger._log_message(json.dumps(snapshot, indent=2))
    else:
        gen_info = ' | '.join([f"{k}: {v}" for k, v in snapshot['generations'].items()])
        obj_info = f" | Total objects: {snapshot.get('total_objects', 'N/A')}" if monitor.dump_objects else ""
        monitor.logger._log_message(f"GMEM SNAPSHOT | {gen_info}{obj_info}")


def dump_objects(monitor):
    """Dump current objects for analysis - ONLY at shutdown."""
    if not (monitor.dump_objects or monitor.dump_garbage):
        return
    
    monitor.logger._log_message("\n=== GC OBJECT DUMP ===")
    
    # gc.get_objects() is expensive but acceptable at shutdown when explicitly requested
    all_objects = gc.get_objects()
    monitor.logger._log_message(f"Total tracked objects: {len(all_objects)}")
    
    # Count objects by type (sample a subset for performance)
    from collections import defaultdict
    type_counts = defaultdict(int)
    sample_size = min(10000, len(all_objects))
    for obj in all_objects[:sample_size]:
        type_counts[type(obj).__name__] += 1
    
    # Show top 10 types
    sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    monitor.logger._log_message("\nTop 10 object types:")
    for obj_type, count in sorted_types:
        monitor.logger._log_message(f"  {obj_type}: {count}")
    
    # Show uncollectable objects if any
    if gc.garbage:
        monitor.logger._log_message(f"\nUncollectable objects ({len(gc.garbage)}):")
        for i, obj in enumerate(gc.garbage[:5]):  # Show first 5
            monitor.logger._log_message(f"  [{i}] {type(obj)}")
        if len(gc.garbage) > 5:
            monitor.logger._log_message(f"  ... and {len(gc.garbage) - 5} more")

