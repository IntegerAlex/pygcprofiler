"""Code generation for gc-util.py monitoring injection."""


def create_monitoring_code(
    interval=5.0,
    json_output=False,
    stats_only=False,
    dump_objects=False,
    dump_garbage=False,
    log_file=None,
    alert_threshold_ms=50.0,
    flamegraph_file=None,
    flamegraph_bucket=5.0,
    duration_buckets=None,
    terminal_flamegraph=False,
    terminal_flamegraph_width=80,
    terminal_flamegraph_color=False,
    live_monitoring=False,
    live_host='127.0.0.1',
    live_port=8989,
    enable_prompt=False
):
    """
    Generate the Python code that will be injected to monitor GC events.
    
    This code follows Zero Runtime Interference principles:
    - Callback only records timestamps and counters
    - No I/O during GC callbacks
    - No memory measurement during runtime
    - All processing happens at shutdown
    """
    duration_buckets = duration_buckets or [1, 5, 20, 50, 100]
    duration_buckets = sorted(set(float(x) for x in duration_buckets if x > 0))
    if not duration_buckets:
        duration_buckets = [1, 5, 20, 50, 100]
    terminal_flamegraph_width = max(int(terminal_flamegraph_width), 40)
    
    from . import templates
    
    monitoring_code = templates.get_monitoring_code_template().format(
        json_output=json_output,
        stats_only=stats_only,
        dump_objects=dump_objects,
        dump_garbage=dump_garbage,
        interval=interval,
        log_file=repr(log_file) if log_file else None,
        alert_threshold_ms=alert_threshold_ms,
        flamegraph_file=repr(flamegraph_file) if flamegraph_file else None,
        flamegraph_bucket=flamegraph_bucket,
        duration_buckets=duration_buckets,
        terminal_flamegraph=terminal_flamegraph,
        terminal_flamegraph_width=terminal_flamegraph_width,
        terminal_flamegraph_color=terminal_flamegraph_color,
        live_monitoring=live_monitoring,
        live_host=repr(live_host),
        live_port=live_port,
    )
    
    return monitoring_code

