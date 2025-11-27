"""Code templates for gc-util.py monitoring injection."""

import textwrap


def get_monitoring_code_template():
    """Get the monitoring code template string."""
    return textwrap.dedent('''
    import gc
    import time
    import sys
    import os
    import json
    import math
    from collections import defaultdict, deque
    import datetime
    
    # Slot indices for event tuples (avoid dict creation in callback)
    _SLOT_REL_TIME = 0
    _SLOT_GENERATION = 1
    _SLOT_DURATION_MS = 2
    _SLOT_COLLECTED = 3
    _SLOT_UNCOLLECTABLE = 4
    
    class UdpEmitter:
        """Fire-and-forget UDP emitter for live monitoring."""
        __slots__ = ('sock', 'address', 'enabled')

        def __init__(self, host='127.0.0.1', port=8989):
            self.address = (host, port)
            self.enabled = True
            try:
                import socket
                self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                self.sock.setblocking(False)
            except Exception:
                self.enabled = False

        def emit(self, event_data):
            if not self.enabled:
                return
            try:
                payload = json.dumps(event_data).encode('utf-8')
                self.sock.sendto(payload, self.address)
            except Exception:
                pass
    
    class GCMonitor:
        """Zero Runtime Interference GC Monitor."""
        
        def __init__(self):
            self.start_perf = time.perf_counter()
            self.start_time = time.time()
            self._collection_starts = [0.0, 0.0, 0.0]
            self._event_buffer = []
            
            # Configuration
            self.json_output = {json_output}
            self.stats_only = {stats_only}
            self.dump_objects = {dump_objects}
            self.dump_garbage = {dump_garbage}
            self.interval = {interval}
            self.log_file = {log_file}
            self.log_handle = None
            self.alert_threshold_ms = {alert_threshold_ms}
            self.flamegraph_file = {flamegraph_file}
            self.flamegraph_bucket = max({flamegraph_bucket}, 0.1)
            self.flamegraph_data = defaultdict(float)
            self.duration_bucket_edges = {duration_buckets}
            self.duration_bucket_labels = self._build_duration_labels()
            palette = ['.', ':', '-', '=', '+', '*', '#', '%', '@']
            self.duration_label_chars = {{label: palette[min(idx, len(palette) - 1)] for idx, label in enumerate(self.duration_bucket_labels)}}
            color_palette = ['\\033[38;5;82m', '\\033[38;5;118m', '\\033[38;5;148m', '\\033[38;5;184m', '\\033[38;5;214m', '\\033[38;5;208m', '\\033[38;5;196m', '\\033[38;5;160m', '\\033[38;5;125m']
            self.duration_label_colors = {{label: color_palette[min(idx, len(color_palette) - 1)] for idx, label in enumerate(self.duration_bucket_labels)}}
            self.terminal_flamegraph = {terminal_flamegraph}
            self.terminal_flamegraph_width = max(int({terminal_flamegraph_width}), 40)
            self.terminal_flamegraph_color = {terminal_flamegraph_color}
            self._ansi_reset = '\\033[0m'
            self._stopped = False
            
            # Live monitoring setup
            self.udp_emitter = None
            if {live_monitoring}:
                self.udp_emitter = UdpEmitter(host={live_host}, port={live_port})
                if not self.udp_emitter.enabled:
                    print("GMEM WARNING: UDP emitter creation failed, live monitoring disabled", file=sys.stderr)
            
            # Statistics
            self.stats = {{
                'total_collections': 0,
                'total_duration_ms': 0.0,
                'collections_by_generation': defaultdict(int),
                'max_duration_ms': 0.0
            }}
            self.collection_timestamps = []
            self.duration_history = defaultdict(lambda: deque(maxlen=200))
            
            if self.dump_garbage:
                gc.set_debug(gc.DEBUG_SAVEALL | gc.DEBUG_UNCOLLECTABLE)
            
            self._original_callbacks = list(gc.callbacks)
            gc.callbacks.append(self._gc_callback)
        
        def __del__(self):
            if self.log_handle:
                self.log_handle.close()
        
        def _gc_callback(self, phase, info):
            generation = info.get('generation', 2)
            if phase == 'start':
                self._collection_starts[generation] = time.perf_counter()
            elif phase == 'stop':
                start_perf = self._collection_starts[generation]
                end_perf = time.perf_counter()
                duration_ms = (end_perf - start_perf) * 1000.0
                collected = info.get('collected', 0)
                uncollectable = info.get('uncollectable', 0)
                relative_time = end_perf - self.start_perf
                self._event_buffer.append((relative_time, generation, duration_ms, collected, uncollectable))
                if self.udp_emitter:
                    self.udp_emitter.emit({{
                        'timestamp': time.time(),
                        'generation': generation,
                        'duration_ms': duration_ms,
                        'collected': collected,
                        'uncollectable': uncollectable
                    }})
        
        def _format_duration(self, duration_ms):
            if duration_ms < 1:
                return f"{{duration_ms:.3f}}ms"
            elif duration_ms < 1000:
                return f"{{duration_ms:.1f}}ms"
            else:
                return f"{{duration_ms/1000:.2f}}s"
        
        def _log_message(self, msg):
            if not self.stats_only:
                print(msg, file=sys.stderr)
            if self.log_handle:
                self.log_handle.write(msg + '\\n')
                self.log_handle.flush()
        
        def _log_event(self, event_data):
            if self.json_output:
                output = json.dumps(event_data, indent=2 if event_data.get('phase') == 'stop' else None)
            else:
                duration_str = self._format_duration(event_data['duration_ms'])
                output = f"GMEM GC STOP  | Gen: {{event_data['generation']}} | Duration: {{duration_str}} | Collected: {{event_data.get('collected', 0)}} | Uncollectable: {{event_data.get('uncollectable', 0)}}"
            self._log_message(output)
        
        def _build_duration_labels(self):
            labels = []
            prev_edge = None
            for edge in self.duration_bucket_edges:
                edge_label = f"{{edge:g}}"
                if prev_edge is None:
                    labels.append(f"<{{edge_label}}ms")
                else:
                    labels.append(f"{{prev_edge:g}}-{{edge_label}}ms")
                prev_edge = edge
            if self.duration_bucket_edges:
                labels.append(f">={{self.duration_bucket_edges[-1]:g}}ms")
            else:
                labels.append(">=0ms")
            return labels
        
        def _duration_bucket(self, duration_ms):
            prev_edge = None
            for edge in self.duration_bucket_edges:
                if duration_ms < edge:
                    if prev_edge is None:
                        return f"<{{edge:g}}ms"
                    return f"{{prev_edge:g}}-{{edge:g}}ms"
                prev_edge = edge
            if self.duration_bucket_edges:
                return f">={{self.duration_bucket_edges[-1]:g}}ms"
            return '>=0ms'
        
        def _percentile(self, samples, percentile):
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
        
        def _record_flamegraph_sample(self, generation, duration_ms, relative_time):
            if not (self.flamegraph_file or self.terminal_flamegraph):
                return
            bucket_index = int(relative_time // self.flamegraph_bucket)
            duration_label = self._duration_bucket(duration_ms)
            key = (bucket_index, generation, duration_label)
            self.flamegraph_data[key] += duration_ms
        
        def _generate_threshold_recommendations(self):
            runtime = max(time.time() - self.start_time, 1)
            recs = []
            for gen, count in self.stats['collections_by_generation'].items():
                per_min = count / (runtime / 60.0)
                if per_min > 800 and gen == 0:
                    recs.append(f"Generation 0 is collecting {{per_min:.0f}} times/min. Consider caching or batching short-lived allocations, or raising gen0 thresholds.")
                samples = list(self.duration_history[gen])
                if samples:
                    avg_duration = sum(samples) / len(samples)
                    p95 = self._percentile(samples, 95)
                    if p95 > self.alert_threshold_ms * 0.8:
                        recs.append(f"Generation {{gen}} p95 pause {{p95:.1f}}ms is approaching/exceeding the {{self.alert_threshold_ms}}ms alert threshold. Tune allocation pressure or trigger GC during idle periods.")
                    if gen == 2 and avg_duration > 10:
                        recs.append(f"Generation 2 average pause {{avg_duration:.1f}}ms. Consider reducing long-lived allocations or forcing collections during low-traffic windows.")
                    long_pauses = sum(1 for sample in samples if sample >= self.alert_threshold_ms)
                    if long_pauses / len(samples) > 0.2:
                        recs.append(f"{{long_pauses/len(samples):.0%}} of Generation {{gen}} pauses exceed the alert threshold. Consider increasing heap headroom or revisiting worker batching.")
            if self.stats['max_duration_ms'] > self.alert_threshold_ms:
                recs.append(f"Observed GC pauses up to {{self._format_duration(self.stats['max_duration_ms'])}} which exceeds the alert threshold of {{self.alert_threshold_ms}}ms. Tune workload or increase heap headroom.")
            duty_cycle = (self.stats['total_duration_ms'] / 1000.0) / runtime
            if duty_cycle > 0.05:
                recs.append(f"GC consumed {{duty_cycle*100:.1f}}% of runtime. Consider increasing interval between memory-intensive tasks or optimizing object lifetimes.")
            if self.collection_timestamps:
                intervals = [self.collection_timestamps[i] - self.collection_timestamps[i - 1] for i in range(1, len(self.collection_timestamps)) if self.collection_timestamps[i] >= self.collection_timestamps[i - 1]]
                if intervals:
                    burst_frequency = sum(1 for v in intervals if v < 0.05)
                    if burst_frequency / len(intervals) > 0.3:
                        recs.append("GC events are bursting faster than 50ms apart. Consider throttling background workers or delaying leak simulations.")
            return recs
        
        def _render_terminal_flamegraph(self):
            if not self.terminal_flamegraph or not self.flamegraph_data:
                return
            rows = defaultdict(lambda: defaultdict(float))
            for (bucket_index, generation, duration_label), duration in self.flamegraph_data.items():
                rows[bucket_index][(generation, duration_label)] += duration
            if not rows:
                self._log_message("No GC flame graph samples collected.")
                return
            use_color = self.terminal_flamegraph_color and sys.stderr.isatty()
            def emit_line(plain_line, colored_line=None):
                if use_color and colored_line:
                    print(colored_line, file=sys.stderr)
                    if self.log_handle:
                        self.log_handle.write(plain_line + '\\n')
                        self.log_handle.flush()
                else:
                    self._log_message(plain_line)
            legend_plain = ", ".join(f"{{self.duration_label_chars[label]}}={{label}}" for label in self.duration_bucket_labels)
            legend_colored = ", ".join(f"{{self.duration_label_colors.get(label, '')}}{{self.duration_label_chars[label]}}{{self._ansi_reset}}={{label}}" for label in self.duration_bucket_labels) if use_color else None
            self._log_message("\\n=== GC FLAME GRAPH (ASCII) ===")
            emit_line(f"Legend: {{legend_plain}}", f"Legend: {{legend_colored}}" if legend_colored else None)
            ordered_buckets = sorted(rows.keys())
            width = self.terminal_flamegraph_width
            for bucket_index in ordered_buckets:
                time_label = f"T+{{int(bucket_index * self.flamegraph_bucket)}}s"
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
                                colored_parts.append(f"{{color}}{{text}}{{self._ansi_reset}}")
                            else:
                                colored_parts.append(text)
                        bar_colored = ''.join(colored_parts)
                    else:
                        bar_colored = bar_plain
                gen_totals = defaultdict(float)
                for (generation, _), duration in bucket.items():
                    gen_totals[generation] += duration
                gen_summary = ', '.join(f"G{{gen}}:{{duration/1000:.1f}}ms" for gen, duration in sorted(gen_totals.items()))
                plain_line = f"{{time_label:>8}} | {{bar_plain}} | {{total_duration/1000:.2f}}ms ({{gen_summary or '—'}})"
                colored_line = f"{{time_label:>8}} | {{bar_colored}} | {{total_duration/1000:.2f}}ms ({{gen_summary or '—'}})" if use_color else None
                emit_line(plain_line, colored_line)
        
        def _process_buffered_events(self):
            for event in self._event_buffer:
                relative_time, generation, duration_ms, collected, uncollectable = event
                absolute_timestamp = self.start_time + relative_time
                self.stats['total_collections'] += 1
                self.stats['total_duration_ms'] += duration_ms
                self.stats['collections_by_generation'][generation] += 1
                self.stats['max_duration_ms'] = max(self.stats['max_duration_ms'], duration_ms)
                self.collection_timestamps.append(absolute_timestamp)
                self.duration_history[generation].append(duration_ms)
                self._record_flamegraph_sample(generation, duration_ms, relative_time)
                if duration_ms >= self.alert_threshold_ms:
                    alert_msg = f"GMEM ALERT | Gen {{generation}} pause {{self._format_duration(duration_ms)}} exceeded {{self.alert_threshold_ms}}ms threshold"
                    self._log_message(alert_msg)
                event_data = {{
                    'timestamp': absolute_timestamp,
                    'phase': 'stop',
                    'generation': generation,
                    'duration_ms': duration_ms,
                    'collected': collected,
                    'uncollectable': uncollectable
                }}
                self._log_event(event_data)
        
        def _dump_objects(self):
            if not (self.dump_objects or self.dump_garbage):
                return
            self._log_message("\\n=== GC OBJECT DUMP ===")
            all_objects = gc.get_objects()
            self._log_message(f"Total tracked objects: {{len(all_objects)}}")
            type_counts = defaultdict(int)
            sample_size = min(10000, len(all_objects))
            for obj in all_objects[:sample_size]:
                type_counts[type(obj).__name__] += 1
            sorted_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)[:10]
            self._log_message("\\nTop 10 object types:")
            for obj_type, count in sorted_types:
                self._log_message(f"  {{obj_type}}: {{count}}")
            if gc.garbage:
                self._log_message(f"\\nUncollectable objects ({{len(gc.garbage)}}):")
                for i, obj in enumerate(gc.garbage[:5]):
                    self._log_message(f"  [{{i}}] {{type(obj)}}")
                if len(gc.garbage) > 5:
                    self._log_message(f"  ... and {{len(gc.garbage) - 5}} more")
        
        def stop_monitoring(self):
            if self._stopped:
                return
            self._stopped = True
            if self._gc_callback in gc.callbacks:
                gc.callbacks.remove(self._gc_callback)
            for callback in self._original_callbacks:
                if callback not in gc.callbacks:
                    gc.callbacks.append(callback)
            if self.log_file:
                self.log_handle = open(self.log_file, 'w')
            self._process_buffered_events()
            self._dump_objects()
            if not self.json_output and not self.stats_only:
                self._log_message("\\n=== GC MONITORING SUMMARY ===")
                self._log_message(f"Total GC collections: {{self.stats['total_collections']}}")
                if self.stats['total_collections'] > 0:
                    avg_duration = self.stats['total_duration_ms'] / self.stats['total_collections']
                    self._log_message(f"Total GC time: {{self._format_duration(self.stats['total_duration_ms'])}}")
                    self._log_message(f"Average GC duration: {{self._format_duration(avg_duration)}}")
                    self._log_message(f"Maximum GC duration: {{self._format_duration(self.stats['max_duration_ms'])}}")
                self._log_message("\\nCollections by generation:")
                for gen, count in sorted(self.stats['collections_by_generation'].items()):
                    self._log_message(f"  Generation {{gen}}: {{count}} collections")
                recommendations = self._generate_threshold_recommendations()
                if recommendations:
                    self._log_message("\\n=== GC THRESHOLD RECOMMENDATIONS ===")
                    for rec in recommendations:
                        self._log_message(f"- {{rec}}")
            if self.flamegraph_file:
                try:
                    with open(self.flamegraph_file, 'w') as flame_file:
                        for (bucket_index, generation, duration_label), duration in self.flamegraph_data.items():
                            time_label = f"T+{{int(bucket_index * self.flamegraph_bucket)}}s"
                            stack = f"{{time_label}};Gen {{generation}};{{duration_label}}"
                            flame_file.write(f"{{stack}} {{duration/1000:.6f}}\\n")
                    self._log_message(f"GC flame graph data written to {{self.flamegraph_file}}")
                except Exception as exc:
                    self._log_message(f"Failed to write flame graph data: {{exc}}")
            if self.terminal_flamegraph:
                self._render_terminal_flamegraph()
            if self.log_handle:
                self.log_handle.close()
                self.log_handle = None
    
    # Initialize monitoring
    print("GMEM Monitoring initialized (Zero Runtime Overhead)", file=sys.stderr)
    monitor = GCMonitor()
    
    # Run the actual script
    try:
        import runpy
        first_arg = sys.argv[1]
        script_args = sys.argv[2:]
        if first_arg == '-m':
            if not script_args:
                print("GMEM Error: Module name required after -m", file=sys.stderr)
                sys.exit(1)
            module_name = script_args[0]
            module_args = script_args[1:]
            sys.argv = ['-m', module_name] + module_args
            runpy.run_module(module_name, run_name="__main__")
        else:
            script_path = first_arg
            script_dir = os.path.dirname(os.path.abspath(script_path))
            if script_dir and script_dir not in sys.path:
                sys.path.insert(0, script_dir)
            sys.argv = [script_path] + script_args
            runpy.run_path(script_path, run_name="__main__")
    except Exception as e:
        print(f"GMEM Error running script: {{str(e)}}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
    finally:
        monitor.stop_monitoring()
    ''')

