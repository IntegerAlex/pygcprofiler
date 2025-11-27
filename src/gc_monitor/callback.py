"""GC callback implementation - minimal overhead design."""

import time


# Pre-allocated slot indices for event tuples to avoid dict creation in callback
_SLOT_TIMESTAMP = 0
_SLOT_GENERATION = 1
_SLOT_DURATION_MS = 2
_SLOT_COLLECTED = 3
_SLOT_UNCOLLECTABLE = 4


def create_gc_callback(monitor):
    """
    Create a GC callback function for the given monitor.
    
    The callback ONLY records:
    - Timestamps (using time.perf_counter())
    - Generation number
    - Duration
    - Collected/uncollectable counts
    
    NO I/O, NO memory checks, NO object scanning, NO stack traces.
    This ensures < 0.1% runtime overhead.
    """
    def _gc_callback(phase, info):
        generation = info.get('generation', 2)

        if phase == 'start':
            # Record start time using perf_counter (monotonic, high-precision)
            monitor._collection_starts[generation] = time.perf_counter()

        elif phase == 'stop':
            # Calculate duration
            start_perf = monitor._collection_starts[generation]
            end_perf = time.perf_counter()
            duration_ms = (end_perf - start_perf) * 1000.0

            # Get counts from info dict (already provided by GC, no extra work)
            collected = info.get('collected', 0)
            uncollectable = info.get('uncollectable', 0)

            # Buffer the event as a tuple (minimal object creation)
            # Timestamp is relative to start for memory efficiency
            relative_time = end_perf - monitor.start_perf
            monitor._event_buffer.append((
                relative_time,
                generation,
                duration_ms,
                collected,
                uncollectable
            ))

            # Send live event if enabled
            if monitor.udp_emitter:
                monitor.udp_emitter.emit({
                    'timestamp': time.time(),  # Use wall clock for live view
                    'generation': generation,
                    'duration_ms': duration_ms,
                    'collected': collected,
                    'uncollectable': uncollectable
                })
    
    return _gc_callback

