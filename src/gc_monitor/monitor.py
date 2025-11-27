"""
Core pygcprofiler implementation - Zero Runtime Interference Design
Copyright (C) 2024  Akshat Kotpalliwar

This library is free software; you can redistribute it and/or
modify it under the terms of the GNU Lesser General Public
License as published by the Free Software Foundation; either
version 2.1 of the License, or (at your option) any later version.

This library is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public
License along with this library; if not, see <https://www.gnu.org/licenses/>.

Design Principles (Zero Runtime Overhead):
- Callback only records timestamps and counters (no I/O, no memory checks)
- Uses time.perf_counter() for high-precision, low-overhead timing
- All output is buffered and written only at shutdown
- No gc.get_objects() or memory measurement during runtime
- No traceback extraction during runtime
- Minimal object creation in callbacks
"""

import gc
import time
import os
import sys
from collections import defaultdict

from .logging import GCLogger
from .stats import GCStatistics
from .flamegraph import FlameGraphRenderer


# Pre-allocated slot indices for event tuples to avoid dict creation in callback
_SLOT_TIMESTAMP = 0
_SLOT_GENERATION = 1
_SLOT_DURATION_MS = 2
_SLOT_COLLECTED = 3
_SLOT_UNCOLLECTABLE = 4


class GCMonitor:
    """
    Main GC monitoring class - Zero Runtime Interference Design
    
    The callback only records:
    - Timestamps (using time.perf_counter())
    - Generation number
    - Duration
    - Collected/uncollectable counts (from GC info dict)
    
    What we NEVER do in the callback:
    - gc.get_objects() - expensive object graph scan
    - gc.collect() - would trigger more GC
    - gc.set_threshold() - would modify GC behavior
    - gc.freeze() - would modify GC behavior
    - I/O operations (print, file write)
    - Memory measurement (psutil calls)
    - Stack trace extraction
    """

    __slots__ = (
        'start_time', 'start_perf', '_stopped', 'interval', 'json_output',
        'stats_only', 'dump_objects', 'dump_garbage', 'alert_threshold_ms',
        'flamegraph_file', 'terminal_flamegraph', 'terminal_flamegraph_width',
        'terminal_flamegraph_color', 'logger', 'stats', 'flame_renderer',
        '_original_callbacks', '_collection_starts', '_event_buffer',
        '_config'
    )

    def __init__(self, **config):
        # Use perf_counter for high-precision timing within the process
        self.start_perf = time.perf_counter()
        # Keep wall-clock time for reporting purposes only
        self.start_time = time.time()
        self._stopped = False

        # Store config for deferred initialization
        self._config = config

        # Configuration
        self.interval = config.get('interval', 5.0)
        self.json_output = config.get('json_output', False)
        self.stats_only = config.get('stats_only', False)
        self.dump_objects = config.get('dump_objects', False)
        self.dump_garbage = config.get('dump_garbage', False)
        self.alert_threshold_ms = config.get('alert_threshold_ms', 50.0)
        self.flamegraph_file = config.get('flamegraph_file')
        self.terminal_flamegraph = config.get('terminal_flamegraph', False)
        self.terminal_flamegraph_width = config.get('terminal_flamegraph_width', 80)
        self.terminal_flamegraph_color = config.get('terminal_flamegraph_color', False)

        # Pre-allocate collection start tracking (one slot per generation)
        # Using a list instead of dict for faster access
        self._collection_starts = [0.0, 0.0, 0.0]  # perf_counter values for gen 0, 1, 2

        # Event buffer: list of tuples (timestamp, generation, duration_ms, collected, uncollectable)
        # Using tuples instead of dicts to minimize object creation
        self._event_buffer = []

        # Defer logger/stats/flame_renderer initialization - they're only needed at shutdown
        self.logger = None
        self.stats = None
        self.flame_renderer = None

        # Enable GC debugging if needed (this is acceptable at init time)
        if self.dump_garbage:
            gc.set_debug(gc.DEBUG_SAVEALL | gc.DEBUG_UNCOLLECTABLE)

        # Register our callback
        self._original_callbacks = list(gc.callbacks)
        gc.callbacks.append(self._gc_callback)

    def _gc_callback(self, phase, info):
        """
        Minimal callback - ONLY records timestamps and counters.
        
        NO I/O, NO memory checks, NO object scanning, NO stack traces.
        This ensures < 0.1% runtime overhead.
        """
        generation = info.get('generation', 2)

        if phase == 'start':
            # Record start time using perf_counter (monotonic, high-precision)
            self._collection_starts[generation] = time.perf_counter()

        elif phase == 'stop':
            # Calculate duration
            start_perf = self._collection_starts[generation]
            end_perf = time.perf_counter()
            duration_ms = (end_perf - start_perf) * 1000.0

            # Get counts from info dict (already provided by GC, no extra work)
            collected = info.get('collected', 0)
            uncollectable = info.get('uncollectable', 0)

            # Buffer the event as a tuple (minimal object creation)
            # Timestamp is relative to start for memory efficiency
            relative_time = end_perf - self.start_perf
            self._event_buffer.append((
                relative_time,
                generation,
                duration_ms,
                collected,
                uncollectable
            ))

    def _initialize_components(self):
        """Lazily initialize logging/stats/flamegraph components at shutdown."""
        if self.logger is not None:
            return  # Already initialized

        self.logger = GCLogger(
            json_output=self.json_output,
            stats_only=self.stats_only,
            log_file=self._config.get('log_file')
        )
        self.stats = GCStatistics(alert_threshold_ms=self.alert_threshold_ms)
        self.stats.start_time = self.start_time

        if self.flamegraph_file or self.terminal_flamegraph:
            self.flame_renderer = FlameGraphRenderer(
                bucket_size=self._config.get('flamegraph_bucket', 5.0),
                duration_buckets=self._config.get('duration_buckets'),
                width=self.terminal_flamegraph_width,
                use_color=self.terminal_flamegraph_color
            )
            self.flame_renderer.start_time = self.start_time

    def _process_buffered_events(self):
        """Process all buffered events at shutdown - this is where we do the heavy lifting."""
        self._initialize_components()

        for event in self._event_buffer:
            relative_time, generation, duration_ms, collected, uncollectable = event

            # Convert relative time back to absolute timestamp for reporting
            absolute_timestamp = self.start_time + relative_time

            # Update statistics
            self.stats.record_collection(generation, duration_ms, absolute_timestamp)

            # Record flamegraph sample
            if self.flame_renderer:
                self.flame_renderer.record_sample(generation, duration_ms, absolute_timestamp)

            # Log the event (I/O happens here, at shutdown)
            event_data = {
                'timestamp': absolute_timestamp,
                'phase': 'stop',
                'generation': generation,
                'duration_ms': duration_ms,
                'collected': collected,
                'uncollectable': uncollectable
            }

            # Check for alerts (threshold exceeded)
            if duration_ms >= self.alert_threshold_ms:
                alert_msg = f"GMEM ALERT | Gen {generation} pause {self.logger._format_duration(duration_ms)} exceeded {self.alert_threshold_ms}ms threshold"
                self.logger.log_alert(alert_msg)

            self.logger.log_event(event_data)

    def _get_memory_usage(self):
        """Get current memory usage in bytes - ONLY called at shutdown."""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return process.memory_info().rss
        except (ImportError, Exception):
            # Return 0 instead of calling gc.get_objects()
            # We don't want to scan the object graph even at shutdown if psutil isn't available
            return 0

    def _take_snapshot(self):
        """Take snapshot of GC state - ONLY called at shutdown."""
        if self.stats_only:
            return

        self._initialize_components()

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
        if self.dump_objects:
            snapshot['total_objects'] = len(gc.get_objects())

        if self.json_output:
            self.logger._log_message(__import__('json').dumps(snapshot, indent=2))
        else:
            gen_info = ' | '.join([f"{k}: {v}" for k, v in snapshot['generations'].items()])
            obj_info = f" | Total objects: {snapshot.get('total_objects', 'N/A')}" if self.dump_objects else ""
            self.logger._log_message(f"GMEM SNAPSHOT | {gen_info}{obj_info}")

    def _dump_objects(self):
        """Dump current objects for analysis - ONLY called at shutdown."""
        if not (self.dump_objects or self.dump_garbage):
            return

        self._initialize_components()

        self.logger._log_message("\n=== GC OBJECT DUMP ===")
        
        # gc.get_objects() is expensive but acceptable at shutdown when explicitly requested
        all_objects = gc.get_objects()
        self.logger._log_message(f"Total tracked objects: {len(all_objects)}")

        # Count objects by type (sample a subset for performance)
        type_counts = defaultdict(int)
        sample_size = min(10000, len(all_objects))
        for obj in all_objects[:sample_size]:
            type_counts[type(obj).__name__] += 1

        # Show top 10 types
        sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:10]
        self.logger._log_message("\nTop 10 object types:")
        for obj_type, count in sorted_types:
            self.logger._log_message(f"  {obj_type}: {count}")

        # Show uncollectable objects if any
        if gc.garbage:
            self.logger._log_message(f"\nUncollectable objects ({len(gc.garbage)}):")
            for i, obj in enumerate(gc.garbage[:5]):  # Show first 5
                self.logger._log_message(f"  [{i}] {type(obj)}")
            if len(gc.garbage) > 5:
                self.logger._log_message(f"  ... and {len(gc.garbage) - 5} more")

    def __del__(self):
        self.stop_monitoring()

    def stop_monitoring(self):
        """Stop monitoring and show final stats - ALL I/O happens here."""
        if self._stopped:
            return
        self._stopped = True

        # Remove our callback first
        if self._gc_callback in gc.callbacks:
            gc.callbacks.remove(self._gc_callback)

        # Restore original callbacks
        for callback in self._original_callbacks:
            if callback not in gc.callbacks:
                gc.callbacks.append(callback)

        # Now process all buffered events (I/O happens here)
        self._process_buffered_events()

        # Take final snapshot if requested
        self._take_snapshot()

        # Dump objects if requested
        self._dump_objects()

        # Initialize components if not already done
        self._initialize_components()

        # Show final statistics
        if not self.json_output and not self.stats_only:
            summary_stats = self.stats.get_summary_stats()
            self.logger._log_message("\n=== GC MONITORING SUMMARY ===")
            self.logger._log_message(f"Total GC collections: {summary_stats['total_collections']}")

            if summary_stats['total_collections'] > 0:
                self.logger._log_message(f"Total GC time: {self.logger._format_duration(summary_stats['total_gc_time'])}")
                self.logger._log_message(f"Average GC duration: {self.logger._format_duration(summary_stats['average_duration'])}")
                self.logger._log_message(f"Maximum GC duration: {self.logger._format_duration(summary_stats['max_duration'])}")

            self.logger._log_message("\nCollections by generation:")
            for gen, count in sorted(summary_stats['collections_by_generation'].items()):
                self.logger._log_message(f"  Generation {gen}: {count} collections")

            recommendations = self.stats.generate_threshold_recommendations()
            if recommendations:
                self.logger._log_message("\n=== GC THRESHOLD RECOMMENDATIONS ===")
                for rec in recommendations:
                    self.logger._log_message(f"- {rec}")

        if self.flamegraph_file and self.flame_renderer:
            result = self.flame_renderer.write_flame_graph_file(self.flamegraph_file, self.start_time)
            if result is True:
                self.logger._log_message(f"GC flame graph data written to {self.flamegraph_file}")
            else:
                self.logger._log_message(result)

        if self.terminal_flamegraph and self.flame_renderer:
            flame_output = self.flame_renderer.render_terminal_flamegraph(self.start_time)
            if isinstance(flame_output, list):
                for line_info in flame_output:
                    if line_info[0] == 'colored':
                        _, plain_line, colored_line = line_info
                        print(colored_line, file=sys.stderr)
                        if self.logger.log_handle:
                            self.logger.log_handle.write(plain_line + '\n')
                            self.logger.log_handle.flush()
                    else:
                        _, plain_line = line_info
                        self.logger._log_message(plain_line)
            else:
                self.logger._log_message(flame_output)

        # Detect GC blunders and generate AI optimization prompt
        blunders, recommendations = self._detect_gc_blunders()
        if blunders:
            self.logger._log_message("\n=== GC BLUNDERS DETECTED ===")
            for blunder in blunders:
                self.logger._log_message(f"[{blunder['severity'].upper()}] {blunder['type'].replace('_', ' ').title()}")
                self.logger._log_message(f"  Metric: {blunder['metric']}")
                self.logger._log_message(f"  Impact: {blunder['impact']}")

        if recommendations:
            self.logger._log_message("\n=== AI OPTIMIZATION RECOMMENDATIONS ===")
            for rec in recommendations:
                self.logger._log_message(f"- {rec}")

        # Generate comprehensive AI prompt
        ai_prompt = self._generate_ai_prompt(blunders, recommendations)
        if ai_prompt:
            self.logger._log_message("\n=== AI OPTIMIZATION PROMPT ===")
            self.logger._log_message("Copy the following prompt to an AI assistant for expert GC optimization:")
            self.logger._log_message(ai_prompt)

    def _detect_gc_blunders(self):
        """Detect common GC performance issues and generate AI prompts"""
        blunders = []
        recommendations = []
        totals = self.stats.stats
        gen2_collections = totals['collections_by_generation'].get(2, 0)
        total_collections = totals['total_collections']

        if total_collections > 0 and gen2_collections / total_collections > 0.1:
            blunders.append({
                'type': 'excessive_gen2_collections',
                'severity': 'high',
                'metric': f"{gen2_collections} Gen 2 collections out of {total_collections} total",
                'impact': 'Causes long application pauses and high latency spikes'
            })
            recommendations.append("Consider using gc.freeze() after application initialization to move startup objects to permanent generation")

        if totals['max_duration_ms'] > 50:
            severity = 'critical' if totals['max_duration_ms'] > 100 else 'high'
            blunders.append({
                'type': 'long_gc_pauses',
                'severity': severity,
                'metric': f"Maximum GC pause: {totals['max_duration_ms']:.1f}ms",
                'impact': 'Causes user-visible latency spikes and poor application responsiveness'
            })
            recommendations.append("Increase GC thresholds dramatically (e.g., from default 700 to 50,000) to reduce collection frequency")

        total_time = time.time() - self.start_time
        gc_cpu_percent = (totals['total_duration_ms'] / 1000) / total_time * 100 if total_time > 0 else 0

        if gc_cpu_percent > 2:
            severity = 'critical' if gc_cpu_percent > 5 else 'high'
            blunders.append({
                'type': 'high_gc_cpu_usage',
                'severity': severity,
                'metric': f"GC uses {gc_cpu_percent:.1f}% of total CPU time",
                'impact': f"Represents approximately {gc_cpu_percent/0.35:.1f}% of allocated cloud resources wasted on garbage collection"
            })
            recommendations.append("Combine gc.freeze() with threshold tuning for optimal performance")

        # Count uncollectable from buffered events
        total_uncollectable = sum(event[_SLOT_UNCOLLECTABLE] for event in self._event_buffer)
        if total_uncollectable > 100:
            blunders.append({
                'type': 'uncollectable_objects',
                'severity': 'medium',
                'metric': f"{total_uncollectable} uncollectable objects found",
                'impact': 'Memory leaks and inefficient memory usage'
            })
            recommendations.append("Investigate reference cycles and consider using weak references or manual cleanup")

        return blunders, recommendations

    def _generate_ai_prompt(self, blunders, recommendations):
        """Generate a comprehensive prompt for AI agents to fix GC issues."""
        from .prompts import PromptBuilder

        builder = PromptBuilder(
            stats=self.stats,
            events=self._event_buffer,
            start_time=self.start_time,
            alert_threshold_ms=self.alert_threshold_ms,
        )
        return builder.build()
