"""Event processing logic for GCMonitor."""

import time
import sys

from .logging import GCLogger
from .stats import GCStatistics
from .flamegraph import FlameGraphRenderer


def process_buffered_events(monitor):
    """Process all buffered events at shutdown - this is where we do the heavy lifting."""
    monitor._initialize_components()

    for event in monitor._event_buffer:
        relative_time, generation, duration_ms, collected, uncollectable = event

        # Convert relative time back to absolute timestamp for reporting
        absolute_timestamp = monitor.start_time + relative_time

        # Update statistics
        monitor.stats.record_collection(generation, duration_ms, absolute_timestamp)

        # Record flamegraph sample
        if monitor.flame_renderer:
            monitor.flame_renderer.record_sample(generation, duration_ms, absolute_timestamp)

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
        if duration_ms >= monitor.alert_threshold_ms:
            alert_msg = f"GMEM ALERT | Gen {generation} pause {monitor.logger._format_duration(duration_ms)} exceeded {monitor.alert_threshold_ms}ms threshold"
            monitor.logger.log_alert(alert_msg)

        monitor.logger.log_event(event_data)


def generate_final_output(monitor):
    """Generate final statistics and recommendations output."""
    if not monitor.json_output and not monitor.stats_only:
        monitor.logger._log_message("\n=== GC MONITORING SUMMARY ===")
        monitor.logger._log_message(f"Total GC collections: {monitor.stats.stats['total_collections']}")
        
        if monitor.stats.stats['total_collections'] > 0:
            avg_duration = monitor.stats.stats['total_duration_ms'] / monitor.stats.stats['total_collections']
            monitor.logger._log_message(f"Total GC time: {monitor.logger._format_duration(monitor.stats.stats['total_duration_ms'])}")
            monitor.logger._log_message(f"Average GC duration: {monitor.logger._format_duration(avg_duration)}")
            monitor.logger._log_message(f"Maximum GC duration: {monitor.logger._format_duration(monitor.stats.stats['max_duration_ms'])}")
        
        monitor.logger._log_message("\nCollections by generation:")
        for gen, count in sorted(monitor.stats.stats['collections_by_generation'].items()):
            monitor.logger._log_message(f"  Generation {gen}: {count} collections")
        
        recommendations = monitor.stats.generate_threshold_recommendations()
        if recommendations:
            monitor.logger._log_message("\n=== GC THRESHOLD RECOMMENDATIONS ===")
            for rec in recommendations:
                monitor.logger._log_message(f"- {rec}")

    if monitor.flamegraph_file and monitor.flame_renderer:
        result = monitor.flame_renderer.write_flame_graph_file(monitor.flamegraph_file, monitor.start_time)
        if result is True:
            monitor.logger._log_message(f"GC flame graph data written to {monitor.flamegraph_file}")
        else:
            monitor.logger._log_message(result)

    if monitor.terminal_flamegraph and monitor.flame_renderer:
        flame_output = monitor.flame_renderer.render_terminal_flamegraph(monitor.start_time)
        if isinstance(flame_output, list):
            for line_info in flame_output:
                # `render_terminal_flamegraph` can return both raw strings and
                # tagged tuples like ('plain', line) or ('colored', plain, colored).
                if isinstance(line_info, tuple):
                    tag = line_info[0]
                    if tag == 'colored':
                        _, plain_line, colored_line = line_info
                    print(colored_line, file=sys.stderr)
                    if monitor.logger.log_handle:
                        monitor.logger.log_handle.write(plain_line + '\n')
                        monitor.logger.log_handle.flush()
                else:
                    _, plain_line = line_info
                    monitor.logger._log_message(plain_line)
            else:
                    # Simple string line
                    monitor.logger._log_message(line_info)
        else:
            monitor.logger._log_message(flame_output)

