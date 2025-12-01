"""
Logging utilities for pygcprofiler events
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

import datetime
import json
import sys

from typing_extensions import deprecated


@deprecated(
    "Programmatic use of pygcprofiler (GCLogger) is deprecated. "
    "Please use the CLI entrypoint `pygcprofiler run ...` instead."
)
class GCLogger:
    """Handles logging for GC monitoring events"""

    def __init__(self, json_output=False, stats_only=False, log_file=None):
        self.json_output = json_output
        self.stats_only = stats_only
        self.log_file = log_file
        self.log_handle = None

        if self.log_file:
            self.log_handle = open(self.log_file, 'w')

    def __del__(self):
        if self.log_handle:
            self.log_handle.close()

    def _log_message(self, msg):
        """Log message to stderr and optionally to file"""
        if not self.stats_only:
            print(msg, file=sys.stderr)

        if self.log_handle:
            self.log_handle.write(msg + '\n')
            self.log_handle.flush()

    def log_event(self, event_data):
        """Log GC event"""
        if self.json_output:
            output = json.dumps(event_data, indent=2 if event_data.get('phase') == 'stop' else None)
        else:
            if event_data['phase'] == 'start':
                timestamp_str = datetime.datetime.fromtimestamp(event_data['timestamp']).strftime('%H:%M:%S.%f')[:-3]
                output = f"GMEM GC START | Gen: {event_data['generation']} | Time: {timestamp_str}"
            else:
                duration_str = self._format_duration(event_data['duration_ms'])
                output = f"GMEM GC STOP  | Gen: {event_data['generation']} | Duration: {duration_str} | Collected: {event_data.get('collected', 0)} | Uncollectable: {event_data.get('uncollectable', 0)}"

                if 'memory_before' in event_data and 'memory_after' in event_data:
                    mem_diff = event_data['memory_before'] - event_data['memory_after']
                    if mem_diff > 0:
                        output += f" | Memory reclaimed: {mem_diff/1024/1024:.2f}MB"

        self._log_message(output)

    def log_alert(self, alert_msg):
        """Log alert message"""
        self._log_message(alert_msg)

    def log_info(self, msg):
        """Log informational message"""
        self._log_message(msg)

    @staticmethod
    def _format_duration(duration_ms):
        """Format duration in human-readable format"""
        if duration_ms < 1:
            return f"{duration_ms:.3f}ms"
        elif duration_ms < 1000:
            return f"{duration_ms:.1f}ms"
        else:
            return f"{duration_ms/1000:.2f}s"
