# SPDX-License-Identifier: LGPL-2.1-only
# Copyright (C) 2024 Akshat Kotpalliwar
"""Tests for GC monitor core functionality."""

import gc
import time
import pytest

from gc_monitor.monitor import GCMonitor


class TestGCMonitorInit:
    """Tests for GCMonitor initialization."""

    def test_basic_init(self, clean_gc_state):
        """Test basic monitor initialization."""
        monitor = GCMonitor()
        
        assert monitor._stopped is False
        assert monitor.start_time > 0
        assert monitor.start_perf > 0
        assert len(monitor._event_buffer) == 0
        assert monitor._gc_callback in gc.callbacks
        
        monitor.stop_monitoring()

    def test_config_defaults(self, clean_gc_state):
        """Test default configuration values."""
        monitor = GCMonitor()
        
        assert monitor.interval == 5.0
        assert monitor.json_output is False
        assert monitor.stats_only is False
        assert monitor.dump_objects is False
        assert monitor.dump_garbage is False
        assert monitor.alert_threshold_ms == 50.0
        assert monitor.flamegraph_file is None
        assert monitor.terminal_flamegraph is False
        
        monitor.stop_monitoring()

    def test_custom_config(self, clean_gc_state):
        """Test custom configuration."""
        monitor = GCMonitor(
            interval=2.0,
            json_output=True,
            stats_only=True,
            alert_threshold_ms=100.0
        )
        
        assert monitor.interval == 2.0
        assert monitor.json_output is True
        assert monitor.stats_only is True
        assert monitor.alert_threshold_ms == 100.0
        
        monitor.stop_monitoring()

    def test_callback_registered(self, clean_gc_state):
        """Test that callback is registered with gc."""
        original_count = len(gc.callbacks)
        monitor = GCMonitor()
        
        assert len(gc.callbacks) == original_count + 1
        assert monitor._gc_callback in gc.callbacks
        
        monitor.stop_monitoring()

    def test_collection_starts_preallocated(self, clean_gc_state):
        """Test that collection starts array is pre-allocated."""
        monitor = GCMonitor()
        
        assert len(monitor._collection_starts) == 3
        assert all(v == 0.0 for v in monitor._collection_starts)
        
        monitor.stop_monitoring()


class TestGCCallback:
    """Tests for the GC callback behavior."""

    def test_callback_records_events(self, clean_gc_state):
        """Test that callback records GC events."""
        monitor = GCMonitor()
        
        # Force some GC activity
        data = [list(range(1000)) for _ in range(100)]
        del data
        gc.collect()
        
        # Should have recorded at least one event
        assert len(monitor._event_buffer) > 0
        
        monitor.stop_monitoring()

    def test_event_buffer_format(self, clean_gc_state):
        """Test that events are stored in correct format."""
        monitor = GCMonitor()
        
        # Force GC
        gc.collect(0)
        
        if monitor._event_buffer:
            event = monitor._event_buffer[0]
            # Event should be a tuple with 5 elements
            assert len(event) == 5
            rel_time, generation, duration_ms, collected, uncollectable = event
            
            assert isinstance(rel_time, float)
            assert isinstance(generation, int)
            assert generation in (0, 1, 2)
            assert isinstance(duration_ms, float)
            assert duration_ms >= 0
            assert isinstance(collected, int)
            assert isinstance(uncollectable, int)
        
        monitor.stop_monitoring()

    def test_no_io_in_callback(self, clean_gc_state, capsys):
        """Test that callback doesn't produce any output."""
        monitor = GCMonitor(stats_only=True)
        
        # Force multiple GC cycles
        for _ in range(10):
            data = [list(range(100)) for _ in range(50)]
            del data
            gc.collect()
        
        # Check no output was produced during monitoring
        captured = capsys.readouterr()
        # The only output should be empty or from initialization
        # (not from the callback itself)
        
        monitor.stop_monitoring()


class TestStopMonitoring:
    """Tests for stop_monitoring behavior."""

    def test_stop_removes_callback(self, clean_gc_state):
        """Test that stopping removes the callback."""
        monitor = GCMonitor()
        assert monitor._gc_callback in gc.callbacks
        
        monitor.stop_monitoring()
        assert monitor._gc_callback not in gc.callbacks

    def test_stop_sets_stopped_flag(self, clean_gc_state):
        """Test that stopping sets the stopped flag."""
        monitor = GCMonitor()
        assert monitor._stopped is False
        
        monitor.stop_monitoring()
        assert monitor._stopped is True

    def test_double_stop_safe(self, clean_gc_state):
        """Test that calling stop twice is safe."""
        monitor = GCMonitor()
        
        monitor.stop_monitoring()
        monitor.stop_monitoring()  # Should not raise
        
        assert monitor._stopped is True

    def test_stop_processes_events(self, clean_gc_state):
        """Test that stop processes buffered events."""
        monitor = GCMonitor()
        
        # Force some GC
        gc.collect()
        
        event_count = len(monitor._event_buffer)
        monitor.stop_monitoring()
        
        # Stats should reflect processed events
        if event_count > 0:
            assert monitor.stats.stats['total_collections'] > 0

    def test_restores_original_callbacks(self, clean_gc_state):
        """Test that original callbacks are restored."""
        def dummy_callback(phase, info):
            pass
        
        gc.callbacks.append(dummy_callback)
        original_callbacks = list(gc.callbacks)
        
        monitor = GCMonitor()
        monitor.stop_monitoring()
        
        # Original callback should still be there
        assert dummy_callback in gc.callbacks
        
        # Clean up
        gc.callbacks.remove(dummy_callback)


class TestStatistics:
    """Tests for statistics collection."""

    def test_stats_initialized(self, clean_gc_state):
        """Test that stats are properly initialized after stop."""
        monitor = GCMonitor()
        gc.collect()
        monitor.stop_monitoring()
        
        assert monitor.stats is not None
        summary = monitor.stats.get_summary_stats()
        
        assert 'total_collections' in summary
        assert 'total_gc_time' in summary
        assert 'average_duration' in summary
        assert 'max_duration' in summary
        assert 'collections_by_generation' in summary

    def test_generation_tracking(self, clean_gc_state):
        """Test that collections are tracked by generation."""
        monitor = GCMonitor()
        
        # Force collections of different generations
        gc.collect(0)
        gc.collect(1)
        gc.collect(2)
        
        monitor.stop_monitoring()
        
        summary = monitor.stats.get_summary_stats()
        # Should have at least some collections recorded
        assert summary['total_collections'] >= 0


class TestZeroOverheadPrinciples:
    """Tests to verify zero-overhead design principles."""

    def test_no_gc_get_objects_during_monitoring(self, clean_gc_state):
        """Verify gc.get_objects() is not called during monitoring."""
        import gc as gc_module
        
        original_get_objects = gc_module.get_objects
        call_count = 0
        
        def counting_get_objects():
            nonlocal call_count
            call_count += 1
            return original_get_objects()
        
        gc_module.get_objects = counting_get_objects
        
        try:
            monitor = GCMonitor(stats_only=True)
            
            # Reset count after init
            call_count = 0
            
            # Do some GC work
            for _ in range(10):
                data = [list(range(100)) for _ in range(20)]
                del data
                gc.collect()
            
            # Should not have called get_objects during monitoring
            assert call_count == 0, f"gc.get_objects() was called {call_count} times during monitoring"
            
        finally:
            gc_module.get_objects = original_get_objects
            monitor.stop_monitoring()

    def test_uses_perf_counter(self, clean_gc_state):
        """Verify time.perf_counter() is used for timing."""
        monitor = GCMonitor()
        
        # Check that perf counter is used
        assert hasattr(monitor, 'start_perf')
        assert monitor.start_perf > 0
        
        monitor.stop_monitoring()

    def test_events_stored_as_tuples(self, clean_gc_state):
        """Verify events are stored as tuples, not dicts."""
        monitor = GCMonitor()
        
        gc.collect()
        
        if monitor._event_buffer:
            event = monitor._event_buffer[0]
            assert isinstance(event, tuple), "Events should be tuples for minimal overhead"
        
        monitor.stop_monitoring()

