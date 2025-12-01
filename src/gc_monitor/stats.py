"""
Statistics calculation and threshold recommendations for pygcprofiler
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
"""

import math
import time
from collections import defaultdict, deque

from typing_extensions import deprecated


@deprecated(
    "Programmatic use of pygcprofiler (GCStatistics) is deprecated. "
    "Please use the CLI entrypoint `pygcprofiler run ...` instead."
)
class GCStatistics:
    """Handles GC statistics calculation and threshold recommendations"""

    def __init__(self, alert_threshold_ms=50.0):
        self.alert_threshold_ms = alert_threshold_ms
        self.stats = {
            'total_collections': 0,
            'total_duration_ms': 0.0,
            'collections_by_generation': defaultdict(int),
            'max_duration_ms': 0.0
        }
        self.collection_timestamps = []
        self.duration_history = defaultdict(lambda: deque(maxlen=200))

    def record_collection(self, generation, duration_ms, timestamp):
        """Record a GC collection event"""
        self.stats['total_collections'] += 1
        self.stats['total_duration_ms'] += duration_ms
        self.stats['collections_by_generation'][generation] += 1
        self.stats['max_duration_ms'] = max(self.stats['max_duration_ms'], duration_ms)

        self.collection_timestamps.append(timestamp)
        self.duration_history[generation].append(duration_ms)

    def get_summary_stats(self):
        """Get summary statistics"""
        if self.stats['total_collections'] > 0:
            avg_duration = self.stats['total_duration_ms'] / self.stats['total_collections']
        else:
            avg_duration = 0.0

        return {
            'total_collections': self.stats['total_collections'],
            'total_gc_time': self.stats['total_duration_ms'],
            'average_duration': avg_duration,
            'max_duration': self.stats['max_duration_ms'],
            'collections_by_generation': dict(self.stats['collections_by_generation'])
        }

    def generate_threshold_recommendations(self):
        """Generate threshold-based recommendations"""
        runtime = max(time.time() - self.start_time, 1) if hasattr(self, 'start_time') else 1
        recs = []

        for gen, count in self.stats['collections_by_generation'].items():
            per_min = count / (runtime / 60.0)
            if per_min > 800 and gen == 0:
                recs.append(f"Generation 0 is collecting {per_min:.0f} times/min. Consider caching or batching short-lived allocations, or raising gen0 thresholds.")

            samples = list(self.duration_history[gen])
            if samples:
                avg_duration = sum(samples) / len(samples)
                p95 = self._percentile(samples, 95)
                if p95 > self.alert_threshold_ms * 0.8:
                    recs.append(f"Generation {gen} p95 pause {p95:.1f}ms is approaching/exceeding the {self.alert_threshold_ms}ms alert threshold. Tune allocation pressure or trigger GC during idle periods.")
                if gen == 2 and avg_duration > 10:
                    recs.append(f"Generation 2 average pause {avg_duration:.1f}ms. Consider reducing long-lived allocations or forcing collections during low-traffic windows.")
                long_pauses = sum(1 for sample in samples if sample >= self.alert_threshold_ms)
                if long_pauses / len(samples) > 0.2:
                    recs.append(f"{long_pauses/len(samples):.0%} of Generation {gen} pauses exceed the alert threshold. Consider increasing heap headroom or revisiting worker batching.")

        if self.stats['max_duration_ms'] > self.alert_threshold_ms:
            recs.append(f"Observed GC pauses up to {self._format_duration(self.stats['max_duration_ms'])} which exceeds the alert threshold of {self.alert_threshold_ms}ms. Tune workload or increase heap headroom.")

        duty_cycle = (self.stats['total_duration_ms'] / 1000.0) / runtime
        if duty_cycle > 0.05:
            recs.append(f"GC consumed {duty_cycle*100:.1f}% of runtime. Consider increasing interval between memory-intensive tasks or optimizing object lifetimes.")

        if self.collection_timestamps:
            intervals = [
                self.collection_timestamps[i] - self.collection_timestamps[i - 1]
                for i in range(1, len(self.collection_timestamps))
                if self.collection_timestamps[i] >= self.collection_timestamps[i - 1]
            ]
            if intervals:
                burst_frequency = sum(1 for v in intervals if v < 0.05)
                if burst_frequency / len(intervals) > 0.3:
                    recs.append("GC events are bursting faster than 50ms apart. Consider throttling background workers or delaying leak simulations.")

        return recs

    @staticmethod
    def _percentile(samples, percentile):
        """Calculate percentile from samples"""
        if not samples:
            return 0.0
        data = sorted(samples)
        if len(data) == 1:
            return data[0]
        k = (len(data) - 1) * (percentile / 100.0)
        lower = math.floor(k)
        upper = math.ceil(k)
        if lower == upper:
            return data[int(k)]
        return data[lower] + (data[upper] - data[lower]) * (k - lower)

    @staticmethod
    def _format_duration(duration_ms):
        """Format duration in human-readable format"""
        if duration_ms < 1:
            return f"{duration_ms:.3f}ms"
        elif duration_ms < 1000:
            return f"{duration_ms:.1f}ms"
        else:
            return f"{duration_ms/1000:.2f}s"
