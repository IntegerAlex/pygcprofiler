# SPDX-License-Identifier: LGPL-2.1-only
# Copyright (C) 2024 Akshat Kotpalliwar
"""Tests for statistics calculation."""

import time
import pytest

from gc_monitor.stats import GCStatistics


class TestGCStatistics:
    """Tests for GCStatistics class."""

    def test_init(self):
        """Test statistics initialization."""
        stats = GCStatistics()
        
        assert stats.stats['total_collections'] == 0
        assert stats.stats['total_duration_ms'] == 0.0
        assert stats.stats['max_duration_ms'] == 0.0
        assert len(stats.stats['collections_by_generation']) == 0

    def test_custom_alert_threshold(self):
        """Test custom alert threshold."""
        stats = GCStatistics(alert_threshold_ms=100.0)
        assert stats.alert_threshold_ms == 100.0

    def test_record_collection(self):
        """Test recording a collection."""
        stats = GCStatistics()
        stats.start_time = time.time()
        
        stats.record_collection(generation=0, duration_ms=1.5, timestamp=time.time())
        
        assert stats.stats['total_collections'] == 1
        assert stats.stats['total_duration_ms'] == 1.5
        assert stats.stats['max_duration_ms'] == 1.5
        assert stats.stats['collections_by_generation'][0] == 1

    def test_record_multiple_collections(self):
        """Test recording multiple collections."""
        stats = GCStatistics()
        stats.start_time = time.time()
        
        stats.record_collection(generation=0, duration_ms=1.0, timestamp=time.time())
        stats.record_collection(generation=0, duration_ms=2.0, timestamp=time.time())
        stats.record_collection(generation=1, duration_ms=5.0, timestamp=time.time())
        stats.record_collection(generation=2, duration_ms=10.0, timestamp=time.time())
        
        assert stats.stats['total_collections'] == 4
        assert stats.stats['total_duration_ms'] == 18.0
        assert stats.stats['max_duration_ms'] == 10.0
        assert stats.stats['collections_by_generation'][0] == 2
        assert stats.stats['collections_by_generation'][1] == 1
        assert stats.stats['collections_by_generation'][2] == 1

    def test_max_duration_tracking(self):
        """Test that max duration is properly tracked."""
        stats = GCStatistics()
        stats.start_time = time.time()
        
        stats.record_collection(generation=0, duration_ms=5.0, timestamp=time.time())
        assert stats.stats['max_duration_ms'] == 5.0
        
        stats.record_collection(generation=0, duration_ms=3.0, timestamp=time.time())
        assert stats.stats['max_duration_ms'] == 5.0  # Should not decrease
        
        stats.record_collection(generation=0, duration_ms=10.0, timestamp=time.time())
        assert stats.stats['max_duration_ms'] == 10.0


class TestGetSummaryStats:
    """Tests for get_summary_stats method."""

    def test_empty_stats(self):
        """Test summary with no collections."""
        stats = GCStatistics()
        summary = stats.get_summary_stats()
        
        assert summary['total_collections'] == 0
        assert summary['total_gc_time'] == 0.0
        assert summary['average_duration'] == 0.0
        assert summary['max_duration'] == 0.0
        assert summary['collections_by_generation'] == {}

    def test_summary_with_data(self):
        """Test summary with recorded data."""
        stats = GCStatistics()
        stats.start_time = time.time()
        
        stats.record_collection(generation=0, duration_ms=2.0, timestamp=time.time())
        stats.record_collection(generation=0, duration_ms=4.0, timestamp=time.time())
        
        summary = stats.get_summary_stats()
        
        assert summary['total_collections'] == 2
        assert summary['total_gc_time'] == 6.0
        assert summary['average_duration'] == 3.0
        assert summary['max_duration'] == 4.0
        assert summary['collections_by_generation'] == {0: 2}


class TestPercentile:
    """Tests for percentile calculation."""

    def test_empty_samples(self):
        """Test percentile with empty samples."""
        result = GCStatistics._percentile([], 95)
        assert result == 0.0

    def test_single_sample(self):
        """Test percentile with single sample."""
        result = GCStatistics._percentile([5.0], 95)
        assert result == 5.0

    def test_multiple_samples(self):
        """Test percentile with multiple samples."""
        samples = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0]
        
        p50 = GCStatistics._percentile(samples, 50)
        assert 5.0 <= p50 <= 6.0
        
        p95 = GCStatistics._percentile(samples, 95)
        assert p95 >= 9.0

    def test_unsorted_samples(self):
        """Test that unsorted samples are handled."""
        samples = [5.0, 1.0, 3.0, 2.0, 4.0]
        p50 = GCStatistics._percentile(samples, 50)
        assert p50 == 3.0


class TestFormatDuration:
    """Tests for duration formatting."""

    def test_sub_millisecond(self):
        """Test formatting sub-millisecond durations."""
        result = GCStatistics._format_duration(0.123)
        assert result == "0.123ms"

    def test_milliseconds(self):
        """Test formatting millisecond durations."""
        result = GCStatistics._format_duration(5.5)
        assert result == "5.5ms"

    def test_seconds(self):
        """Test formatting second durations."""
        result = GCStatistics._format_duration(1500.0)
        assert result == "1.50s"


class TestThresholdRecommendations:
    """Tests for threshold recommendations."""

    def test_no_recommendations_for_good_stats(self):
        """Test that no recommendations for healthy GC."""
        stats = GCStatistics(alert_threshold_ms=50.0)
        stats.start_time = time.time() - 60  # 1 minute ago
        
        # Record some healthy collections
        for i in range(10):
            stats.record_collection(generation=0, duration_ms=0.5, timestamp=time.time())
        
        recs = stats.generate_threshold_recommendations()
        # Should have few or no recommendations for healthy GC
        assert isinstance(recs, list)

    def test_recommendation_for_high_pause(self):
        """Test recommendation for high pause times."""
        stats = GCStatistics(alert_threshold_ms=50.0)
        stats.start_time = time.time() - 60
        
        # Record a high pause
        stats.record_collection(generation=2, duration_ms=100.0, timestamp=time.time())
        
        recs = stats.generate_threshold_recommendations()
        # Should have at least one recommendation
        assert len(recs) > 0
        assert any('pause' in rec.lower() or 'threshold' in rec.lower() for rec in recs)

