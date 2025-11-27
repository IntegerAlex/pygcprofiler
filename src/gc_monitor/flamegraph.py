"""
Flame graph rendering for pygcprofiler
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

import sys
from collections import defaultdict


class FlameGraphRenderer:
    """Handles flame graph rendering for terminal output"""

    def __init__(self, bucket_size=5.0, duration_buckets=None, width=80, use_color=False):
        self.flamegraph_bucket = max(bucket_size, 0.1)
        self.flamegraph_data = defaultdict(float)
        self.duration_bucket_edges = duration_buckets or [1, 5, 20, 50, 100]
        self.duration_bucket_edges = sorted(set(float(x) for x in self.duration_bucket_edges if x > 0))
        if not self.duration_bucket_edges:
            self.duration_bucket_edges = [1, 5, 20, 50, 100]

        self.duration_bucket_labels = self._build_duration_labels()
        palette = ['.', ':', '-', '=', '+', '*', '#', '%', '@']
        self.duration_label_chars = {label: palette[min(idx, len(palette) - 1)] for idx, label in enumerate(self.duration_bucket_labels)}
        color_palette = ['\033[38;5;82m', '\033[38;5;118m', '\033[38;5;148m', '\033[38;5;184m', '\033[38;5;214m', '\033[38;5;208m', '\033[38;5;196m', '\033[38;5;160m', '\033[38;5;125m']
        self.duration_label_colors = {label: color_palette[min(idx, len(color_palette) - 1)] for idx, label in enumerate(self.duration_bucket_labels)}
        self.terminal_flamegraph_width = max(int(width), 40)
        self.terminal_flamegraph_color = use_color
        self._ansi_reset = '\033[0m'

    def record_sample(self, generation, duration_ms, timestamp):
        """Record a flame graph sample"""
        bucket_index = int((timestamp - self.start_time) // self.flamegraph_bucket) if hasattr(self, 'start_time') else 0
        duration_label = self._duration_bucket(duration_ms)
        key = (bucket_index, generation, duration_label)
        self.flamegraph_data[key] += duration_ms

    def write_flame_graph_file(self, filename, start_time):
        """Write collapsed stack-compatible flame graph data to file"""
        try:
            with open(filename, 'w') as flame_file:
                for (bucket_index, generation, duration_label), duration in self.flamegraph_data.items():
                    time_label = f"T+{int(bucket_index * self.flamegraph_bucket)}s"
                    stack = f"{time_label};Gen {generation};{duration_label}"
                    flame_file.write(f"{stack} {duration/1000:.6f}\n")
            return True
        except Exception as exc:
            return f"Failed to write flame graph data: {exc}"

    def render_terminal_flamegraph(self, start_time):
        """Render ASCII flame graph to terminal"""
        if not self.flamegraph_data:
            return "No GC flame graph samples collected."

        rows = defaultdict(lambda: defaultdict(float))
        for (bucket_index, generation, duration_label), duration in self.flamegraph_data.items():
            rows[bucket_index][(generation, duration_label)] += duration

        if not rows:
            return "No GC flame graph samples collected."

        use_color = self.terminal_flamegraph_color and sys.stderr.isatty()

        output_lines = []
        legend_plain = ", ".join(f"{self.duration_label_chars[label]}={label}" for label in self.duration_bucket_labels)

        if use_color:
            legend_colored = ", ".join(
                f"{self.duration_label_colors.get(label, '')}{self.duration_label_chars[label]}{self._ansi_reset}={label}"
                for label in self.duration_bucket_labels
            )
        else:
            legend_colored = None

        output_lines.append("\n=== GC FLAME GRAPH (ASCII) ===")
        output_lines.append(f"Legend: {legend_plain}")

        ordered_buckets = sorted(rows.keys())
        width = self.terminal_flamegraph_width

        for bucket_index in ordered_buckets:
            time_label = f"T+{int(bucket_index * self.flamegraph_bucket)}s"
            bucket = rows[bucket_index]
            total_duration = sum(bucket.values())
            if total_duration <= 0:
                bar_plain = ' ' * width
                bar_colored = bar_plain
            else:
                segments = []
                remaining = width
                for (generation, duration_label), duration in sorted(bucket.items()):
                    share = duration / total_duration
                    segment_width = max(1, int(share * width))
                    char = self.duration_label_chars.get(duration_label, '#')
                    segment_text = char * min(segment_width, remaining)
                    segments.append((duration_label, segment_text))
                    remaining -= segment_width
                    if remaining <= 0:
                        break
                if remaining > 0:
                    segments.append((None, ' ' * remaining))
                bar_plain = ''.join(text for _, text in segments)[:width]
                if use_color:
                    colored_parts = []
                    for label, text in segments:
                        if label and text.strip():
                            color = self.duration_label_colors.get(label, '')
                            colored_parts.append(f"{color}{text}{self._ansi_reset}")
                        else:
                            colored_parts.append(text)
                    bar_colored = ''.join(colored_parts)
                else:
                    bar_colored = bar_plain

            gen_totals = defaultdict(float)
            for (generation, _), duration in bucket.items():
                gen_totals[generation] += duration
            gen_summary = ', '.join(f"G{gen}:{duration/1000:.1f}ms" for gen, duration in sorted(gen_totals.items()))
            plain_line = f"{time_label:>8} | {bar_plain} | {total_duration/1000:.2f}ms ({gen_summary or '—'})"
            colored_line = f"{time_label:>8} | {bar_colored} | {total_duration/1000:.2f}ms ({gen_summary or '—'})" if use_color else None

            if use_color and colored_line:
                # For colored output, we need to handle both stderr and log file
                output_lines.append(('colored', plain_line, colored_line))
            else:
                output_lines.append(('plain', plain_line))

        return output_lines

    def _build_duration_labels(self):
        labels = []
        prev_edge = None
        for edge in self.duration_bucket_edges:
            edge_label = f"{edge:g}"
            if prev_edge is None:
                labels.append(f"<{edge_label}ms")
            else:
                labels.append(f"{prev_edge:g}-{edge_label}ms")
            prev_edge = edge
        if self.duration_bucket_edges:
            labels.append(f">={self.duration_bucket_edges[-1]:g}ms")
        else:
            labels.append(">=0ms")
        return labels

    def _duration_bucket(self, duration_ms):
        prev_edge = None
        for edge in self.duration_bucket_edges:
            if duration_ms < edge:
                if prev_edge is None:
                    return f"<{edge:g}ms"
                return f"{prev_edge:g}-{edge:g}ms"
            prev_edge = edge
        if self.duration_bucket_edges:
            return f">={self.duration_bucket_edges[-1]:g}ms"
        return '>=0ms'
