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

from typing_extensions import deprecated

from .logging import GCLogger
from .stats import GCStatistics
from .flamegraph import FlameGraphRenderer
from .udp_emitter import UdpEmitter
from .callback import create_gc_callback
from .processing import process_buffered_events, generate_final_output
from .utils import take_snapshot, dump_objects
from .blunders import detect_gc_blunders

@deprecated(
    "Programmatic use of pygcprofiler (GCMonitor) is deprecated. "
    "Please use the CLI entrypoint `pygcprofiler run ...` instead."
)
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
        'terminal_flamegraph_color', 'enable_prompt',
        'logger', 'stats', 'flame_renderer',
        '_original_callbacks', '_collection_starts', '_event_buffer',
        '_config', 'udp_emitter', '_gc_callback'
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
        self.terminal_flamegraph_width = config.get('terminal_flamegraph_width', 80)
        self.terminal_flamegraph_color = config.get('terminal_flamegraph_color', False)
        self.enable_prompt = config.get('enable_prompt', False)

        # Live monitoring setup
        self.udp_emitter = None
        if config.get('live_monitoring', False):
            self.udp_emitter = UdpEmitter(
                host=config.get('live_host', '127.0.0.1'),
                port=config.get('live_port', 8989)
            )

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

        # Initialize callback reference (needed for cleanup)
        self._gc_callback = None

        # Enable GC debugging if needed (this is acceptable at init time)
        if self.dump_garbage:
            gc.set_debug(gc.DEBUG_SAVEALL | gc.DEBUG_UNCOLLECTABLE)

        # Register our callback
        self._original_callbacks = list(gc.callbacks)
        self._gc_callback = create_gc_callback(self)
        gc.callbacks.append(self._gc_callback)

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
        process_buffered_events(self)


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
        take_snapshot(self)

        # Dump objects if requested
        dump_objects(self)

        # Initialize components if not already done
        self._initialize_components()

        # Generate final output (stats, flamegraphs, etc.)
        generate_final_output(self)

        # Detect GC blunders and generate AI optimization prompt
        from collections import defaultdict
        _SLOT_UNCOLLECTABLE = 4
        total_uncollectable = sum(event[_SLOT_UNCOLLECTABLE] for event in self._event_buffer)
        
        # Convert events to dict format for blunder detection
        event_dicts = []
        for event in self._event_buffer:
            relative_time, generation, duration_ms, collected, uncollectable = event
            event_dicts.append({
                'generation': generation,
                'duration_ms': duration_ms,
                'collected': collected,
                'uncollectable': uncollectable
            })
        
        blunders, recommendations = detect_gc_blunders(self.stats, event_dicts, self.start_time)
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

        # Generate comprehensive AI prompt only if enabled
        if self.enable_prompt:
            try:
                from .prompts import PromptBuilder
                builder = PromptBuilder(
                    stats=self.stats,
                    events=self._event_buffer,
                    start_time=self.start_time,
                    alert_threshold_ms=self.alert_threshold_ms,
                )
                ai_prompt = builder.build()
                if ai_prompt:
                    self.logger._log_message("\n=== AI OPTIMIZATION PROMPT ===")
                    self.logger._log_message("Copy the following prompt to an AI assistant for expert GC optimization:")
                    self.logger._log_message(ai_prompt)
            except ImportError:
                # Prompts module is optional
                pass

