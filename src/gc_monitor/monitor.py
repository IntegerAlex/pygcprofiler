# SPDX-License-Identifier: LGPL-2.1-only
# Copyright (C) 2024 Akshat Kotpalliwar

"""
Core pygcprofiler implementation
"""

import gc
import time
import os
import sys
from collections import defaultdict, deque

from .logging import GCLogger
from .stats import GCStatistics
from .flamegraph import FlameGraphRenderer


class GCMonitor:
    """Main GC monitoring class that coordinates all monitoring activities"""

    def __init__(self, **config):
        self.start_time = time.time()
        self.last_snapshot_time = self.start_time
        self._stopped = False

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

        # Initialize components
        self.logger = GCLogger(
            json_output=self.json_output,
            stats_only=self.stats_only,
            log_file=config.get('log_file')
        )
        self.stats = GCStatistics(alert_threshold_ms=self.alert_threshold_ms)
        self.stats.start_time = self.start_time  # Pass start time to stats
        self.gc_events = []

        if self.flamegraph_file or self.terminal_flamegraph:
            self.flame_renderer = FlameGraphRenderer(
                bucket_size=config.get('flamegraph_bucket', 5.0),
                duration_buckets=config.get('duration_buckets'),
                width=self.terminal_flamegraph_width,
                use_color=self.terminal_flamegraph_color
            )
            self.flame_renderer.start_time = self.start_time
        else:
            self.flame_renderer = None

        # Enable GC debugging if needed
        if self.dump_garbage:
            gc.set_debug(gc.DEBUG_SAVEALL | gc.DEBUG_UNCOLLECTABLE)

        # Register our callback
        self._original_callbacks = list(gc.callbacks)
        gc.callbacks.append(self._gc_callback)

        # Take initial snapshot
        self._take_snapshot()

    def __del__(self):
        self.stop_monitoring()

    def _get_memory_usage(self):
        """Get current memory usage in bytes"""
        try:
            import psutil
            process = psutil.Process(os.getpid())
            return process.memory_info().rss
        except (ImportError, Exception):
            # Fallback to rough estimate
            return len(gc.get_objects()) * 64

    def _gc_callback(self, phase, info):
        """Callback function for GC events"""
        timestamp = time.time()
        generation = info.get('generation', 2)

        if phase == 'start':
            # Store start time and memory usage
            if not hasattr(self, '_collection_starts'):
                self._collection_starts = {}

            self._collection_starts[generation] = {
                'time': timestamp,
                'memory': self._get_memory_usage() if not self.stats_only else 0
            }

            event_data = {
                'timestamp': timestamp,
                'phase': 'start',
                'generation': generation
            }
            self.logger.log_event(event_data)

        elif phase == 'stop':
            start_info = getattr(self, '_collection_starts', {}).pop(generation, {'time': timestamp, 'memory': 0})

            duration_ms = (timestamp - start_info['time']) * 1000
            collected = info.get('collected', 0)
            uncollectable = info.get('uncollectable', 0)

            if duration_ms >= self.alert_threshold_ms:
                alert_msg = f"GMEM ALERT | Gen {generation} pause {self.logger._format_duration(duration_ms)} exceeded {self.alert_threshold_ms}ms threshold"
                self.logger.log_alert(alert_msg)

            if self.flame_renderer:
                self.flame_renderer.record_sample(generation, duration_ms, timestamp)

            # Update statistics
            self.stats.record_collection(generation, duration_ms, timestamp)

            event_data = {
                'timestamp': timestamp,
                'phase': 'stop',
                'generation': generation,
                'duration_ms': duration_ms,
                'collected': collected,
                'uncollectable': uncollectable
            }

            if not self.stats_only:
                event_data['memory_before'] = start_info['memory']
                event_data['memory_after'] = self._get_memory_usage()

            self.gc_events.append(event_data)
            self.logger.log_event(event_data)

            # Take periodic snapshot if needed
            if time.time() - self.last_snapshot_time >= self.interval:
                self._take_snapshot()
                self.last_snapshot_time = time.time()

    def _take_snapshot(self):
        """Take periodic snapshot of GC state"""
        if self.stats_only:
            return

        snapshot = {
            'timestamp': time.time(),
            'total_objects': len(gc.get_objects()),
            'generations': {}
        }

        try:
            # Get counts for each generation
            counts = gc.get_count()
            snapshot['generations'] = {
                'gen0': counts[0] if len(counts) > 0 else 0,
                'gen1': counts[1] if len(counts) > 1 else 0,
                'gen2': counts[2] if len(counts) > 2 else 0
            }
        except Exception as e:
            snapshot['error'] = str(e)

        if self.json_output:
            self.logger._log_message(__import__('json').dumps(snapshot, indent=2))
        else:
            gen_info = ' | '.join([f"{k}: {v}" for k, v in snapshot['generations'].items()])
            self.logger._log_message(f"GMEM SNAPSHOT | Total objects: {snapshot['total_objects']} | {gen_info}")

    def _dump_objects(self):
        """Dump current objects for analysis"""
        if not (self.dump_objects or self.dump_garbage):
            return

        self.logger._log_message("\n=== GC OBJECT DUMP ===")
        self.logger._log_message(f"Total tracked objects: {len(gc.get_objects())}")

        # Count objects by type (sample a subset for performance)
        type_counts = defaultdict(int)
        sample_size = min(10000, len(gc.get_objects()))
        for obj in gc.get_objects()[:sample_size]:
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

    def stop_monitoring(self):
        """Stop monitoring and show final stats"""
        if getattr(self, "_stopped", False):
            return
        self._stopped = True

        # Remove our callback
        if hasattr(self, '_gc_callback') and self._gc_callback in gc.callbacks:
            gc.callbacks.remove(self._gc_callback)

        # Restore original callbacks
        for callback in self._original_callbacks:
            if callback not in gc.callbacks:
                gc.callbacks.append(callback)

        # Dump objects if requested
        self._dump_objects()

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

        if total_collections > 0 and gen2_collections / total_collections > 0.1:  # More than 10% are full collections
            blunders.append({
                'type': 'excessive_gen2_collections',
                'severity': 'high',
                'metric': f"{gen2_collections} Gen 2 collections out of {total_collections} total",
                'impact': 'Causes long application pauses and high latency spikes'
            })
            recommendations.append("Consider using gc.freeze() after application initialization to move startup objects to permanent generation")

        # Blunder 2: Long GC pauses
        if totals['max_duration_ms'] > 50:  # More than 50ms pause
            severity = 'critical' if totals['max_duration_ms'] > 100 else 'high'
            blunders.append({
                'type': 'long_gc_pauses',
                'severity': severity,
                'metric': f"Maximum GC pause: {totals['max_duration_ms']:.1f}ms",
                'impact': 'Causes user-visible latency spikes and poor application responsiveness'
            })
            recommendations.append("Increase GC thresholds dramatically (e.g., from default 700 to 50,000) to reduce collection frequency")

        # Blunder 3: High CPU usage by GC
        total_time = time.time() - self.start_time
        gc_cpu_percent = (totals['total_duration_ms'] / 1000) / total_time * 100

        if gc_cpu_percent > 2:  # More than 2% CPU spent on GC
            severity = 'critical' if gc_cpu_percent > 5 else 'high'
            blunders.append({
                'type': 'high_gc_cpu_usage',
                'severity': severity,
                'metric': f"GC uses {gc_cpu_percent:.1f}% of total CPU time",
                'impact': f"Represents approximately {gc_cpu_percent/0.35:.1f}% of allocated cloud resources wasted on garbage collection"
            })
            recommendations.append("Combine gc.freeze() with threshold tuning for optimal performance")

        # Blunder 4: Many uncollectable objects
        total_uncollectable = sum(event.get('uncollectable', 0) for event in self.gc_events)
        if total_uncollectable > 100:  # More than 100 uncollectable objects
            blunders.append({
                'type': 'uncollectable_objects',
                'severity': 'medium',
                'metric': f"{total_uncollectable} uncollectable objects found",
                'impact': 'Memory leaks and inefficient memory usage'
            })
            recommendations.append("Investigate reference cycles and consider using weak references or manual cleanup")

        return blunders, recommendations

    def _generate_ai_prompt(self, blunders, recommendations):
        """Generate a comprehensive prompt for AI agents to fix GC issues"""

        current_thresholds = gc.get_threshold()
        current_counts = gc.get_count()
        summary = self.stats.get_summary_stats()
        totals = self.stats.stats
        runtime = max(time.time() - self.start_time, 1)
        issue_lines = [
            f"• [{issue['severity'].upper()}] {issue['type'].replace('_', ' ').title()}: {issue['metric']} - {issue['impact']}"
            for issue in blunders
        ] or ["• None detected during this interval."]
        recommendation_lines = [f"• {rec}" for rec in recommendations] or ["• Collect more data to produce actionable insights."]

        return f"""

🔧 PYTHON GC PERFORMANCE OPTIMIZATION REQUEST

I'm experiencing significant performance issues with Python's garbage collector in a production web application. Please provide specific, actionable optimization strategies.

📊 CURRENT GC METRICS (collected over {runtime:.1f} seconds):

• Total GC Collections: {summary['total_collections']}

• Generation Breakdown:
  - Gen 0: {summary['collections_by_generation'].get(0, 0)} collections
  - Gen 1: {summary['collections_by_generation'].get(1, 0)} collections
  - Gen 2: {summary['collections_by_generation'].get(2, 0)} collections

• Performance Impact:
  - Max GC Pause: {summary['max_duration']:.1f}ms
  - Total GC Time: {summary['total_gc_time']/1000:.2f}s
  - CPU Usage by GC: {(totals['total_duration_ms']/1000)/runtime*100:.1f}%

• Current GC Thresholds: {current_thresholds}

• Current Object Counts: {current_counts}

• Uncollectable Objects Found: {sum(event.get('uncollectable', 0) for event in self.gc_events)}

🚨 DETECTED ISSUES:

{chr(10).join(issue_lines)}

💡 RECOMMENDATIONS TO CONSIDER:

{chr(10).join(recommendation_lines)}

🎯 APPLICATION CONTEXT:

- This is a web application (likely Django/FastAPI/Flask) handling HTTP requests
- We cannot modify the core application code extensively
- We need solutions that can be applied at startup/initialization
- The goal is to reduce p95 latency and improve overall throughput
- We're using standard CPython (not PyPy or other implementations)

🔧 SPECIFIC OPTIMIZATION REQUESTS:

1. Provide EXACT code snippets to place at application startup that will:
   - Freeze initialization objects to prevent them from being scanned in Gen 2
   - Set optimal GC thresholds based on our metrics
   - Add minimal-overhead monitoring for production

2. For each recommendation, explain:
   - WHY it will help our specific metrics
   - WHAT the expected performance improvement will be
   - ANY potential risks or trade-offs
   - HOW to validate the improvement

3. Include production-ready monitoring code that can be integrated with OpenTelemetry or similar observability tools.

4. If applicable, provide strategies to identify and fix the root causes of uncollectable objects.

🚀 FORMAT REQUIREMENTS:

- Provide ready-to-copy code blocks with proper error handling
- Include comments explaining each optimization
- Give specific threshold values based on our metrics (don't use placeholders)
- Prioritize solutions that can be deployed immediately with minimal risk
- Include rollback strategies if optimizations cause issues

Example of the type of code we need at startup:

```python
import gc

# Optimization 1: Clean up and freeze startup objects
gc.collect(2)  # Full collection of all generations
gc.freeze()    # Move all tracked objects to permanent generation

# Optimization 2: Set aggressive thresholds based on our workload
current_gen1, current_gen2 = gc.get_threshold()[1:]
# OUR SPECIFIC THRESHOLDS BASED ON METRICS:
gc.set_threshold(50000, current_gen1, current_gen2)  # Dramatically reduce collection frequency

print(f"GMEM GC optimized: thresholds set to {{gc.get_threshold()}}, {{gc.get_freeze_count()}} objects frozen")
```

"""
