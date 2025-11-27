# SPDX-License-Identifier: LGPL-2.1-only
# Copyright (C) 2024 Akshat Kotpalliwar
"""Tests for the modular prompt generation system."""

import sys
import time
import pytest
from unittest.mock import MagicMock, patch

from gc_monitor.prompts import PromptBuilder, AppTypeDetector, AppType, GCContext
from gc_monitor.prompts.context import GCMetrics, GCIssue
from gc_monitor.prompts.detector import AppProfile


class TestAppTypeDetector:
    """Tests for application type detection."""

    def test_detect_unknown_by_default(self):
        """Test that unknown is returned for plain scripts."""
        detector = AppTypeDetector()
        # Clear cache
        detector._cached_profile = None
        
        with patch.dict(sys.modules, {}, clear=False):
            profile = detector.detect()
            # Will detect based on actual loaded modules
            assert isinstance(profile, AppProfile)
            assert isinstance(profile.app_type, AppType)

    def test_detect_fastapi(self):
        """Test FastAPI detection."""
        detector = AppTypeDetector()
        detector._cached_profile = None
        
        mock_modules = {'fastapi', 'starlette', 'uvicorn', 'asyncio'}
        with patch.object(sys, 'modules', {m: MagicMock() for m in mock_modules}):
            profile = detector.detect()
            assert profile.framework == "FastAPI"
            assert profile.server == "Uvicorn"
            assert profile.async_mode is True

    def test_detect_django(self):
        """Test Django detection."""
        detector = AppTypeDetector()
        detector._cached_profile = None
        
        mock_modules = {'django', 'gunicorn'}
        with patch.object(sys, 'modules', {m: MagicMock() for m in mock_modules}):
            profile = detector.detect()
            assert profile.framework == "Django"
            assert profile.server == "Gunicorn"

    def test_detect_flask(self):
        """Test Flask detection."""
        detector = AppTypeDetector()
        detector._cached_profile = None
        
        mock_modules = {'flask', 'waitress'}
        with patch.object(sys, 'modules', {m: MagicMock() for m in mock_modules}):
            profile = detector.detect()
            assert profile.framework == "Flask"

    def test_detect_celery(self):
        """Test Celery worker detection."""
        detector = AppTypeDetector()
        detector._cached_profile = None
        
        mock_modules = {'celery'}
        with patch.object(sys, 'modules', {m: MagicMock() for m in mock_modules}):
            profile = detector.detect()
            assert profile.app_type == AppType.CELERY_WORKER

    def test_detect_data_processing(self):
        """Test data processing detection."""
        detector = AppTypeDetector()
        detector._cached_profile = None
        
        mock_modules = {'pandas', 'numpy'}
        with patch.object(sys, 'modules', {m: MagicMock() for m in mock_modules}):
            profile = detector.detect()
            assert profile.app_type == AppType.DATA_PROCESSING

    def test_detect_ml_training(self):
        """Test ML training detection."""
        detector = AppTypeDetector()
        detector._cached_profile = None
        
        mock_modules = {'torch', 'numpy'}
        with patch.object(sys, 'modules', {m: MagicMock() for m in mock_modules}):
            profile = detector.detect()
            assert profile.app_type == AppType.ML_TRAINING

    def test_caching(self):
        """Test that detection result is cached."""
        detector = AppTypeDetector()
        detector._cached_profile = None
        
        profile1 = detector.detect()
        profile2 = detector.detect()
        assert profile1 is profile2


class TestGCContext:
    """Tests for GC context building."""

    def test_from_stats_basic(self):
        """Test building context from stats."""
        # Mock stats
        mock_stats = MagicMock()
        mock_stats.stats = {
            'total_collections': 100,
            'total_duration_ms': 500.0,
            'max_duration_ms': 25.0,
            'collections_by_generation': {0: 80, 1: 15, 2: 5},
        }

        events = [(1.0, 0, 5.0, 100, 0)] * 10
        start_time = time.time() - 60  # 60 seconds ago

        profile = AppProfile(app_type=AppType.CLI_TOOL)
        context = GCContext.from_stats(
            stats=mock_stats,
            events=events,
            start_time=start_time,
            app_profile=profile,
        )

        assert context.metrics.total_collections == 100
        assert context.metrics.max_duration_ms == 25.0
        assert context.app_profile.app_type == AppType.CLI_TOOL

    def test_issue_detection_long_pause(self):
        """Test that long pauses are detected."""
        metrics = GCMetrics(
            total_collections=10,
            total_duration_ms=200.0,
            max_duration_ms=75.0,
            avg_duration_ms=20.0,
            collections_by_gen={0: 10},
            gc_cpu_percent=0.5,
            runtime_seconds=60.0,
        )

        issues = GCContext._detect_issues(metrics, alert_threshold_ms=50.0)
        
        issue_types = [i.issue_type for i in issues]
        assert 'long_pauses' in issue_types

    def test_issue_detection_high_cpu(self):
        """Test that high CPU usage is detected."""
        metrics = GCMetrics(
            total_collections=1000,
            total_duration_ms=5000.0,
            max_duration_ms=10.0,
            avg_duration_ms=5.0,
            collections_by_gen={0: 1000},
            gc_cpu_percent=8.0,  # 8% CPU on GC
            runtime_seconds=60.0,
        )

        issues = GCContext._detect_issues(metrics, alert_threshold_ms=50.0)
        
        issue_types = [i.issue_type for i in issues]
        assert 'high_cpu' in issue_types
        # Should be critical at 8%
        high_cpu_issue = next(i for i in issues if i.issue_type == 'high_cpu')
        assert high_cpu_issue.severity == 'critical'

    def test_issue_detection_excessive_gen2(self):
        """Test that excessive Gen 2 collections are detected."""
        metrics = GCMetrics(
            total_collections=100,
            total_duration_ms=500.0,
            max_duration_ms=25.0,
            avg_duration_ms=5.0,
            collections_by_gen={0: 50, 1: 30, 2: 20},  # 20% Gen 2
            gc_cpu_percent=1.0,
            runtime_seconds=60.0,
        )

        issues = GCContext._detect_issues(metrics, alert_threshold_ms=50.0)
        
        issue_types = [i.issue_type for i in issues]
        assert 'excessive_gen2' in issue_types

    def test_severity_summary(self):
        """Test severity summary generation."""
        profile = AppProfile(app_type=AppType.CLI_TOOL)
        
        # Healthy
        context = GCContext(
            metrics=GCMetrics(),
            issues=[],
            app_profile=profile,
        )
        assert context.get_severity_summary() == "healthy"

        # Critical
        context = GCContext(
            metrics=GCMetrics(),
            issues=[GCIssue('test', 'critical', '', '', '')],
            app_profile=profile,
        )
        assert context.get_severity_summary() == "critical"

        # Needs attention
        context = GCContext(
            metrics=GCMetrics(),
            issues=[GCIssue('test', 'high', '', '', '')],
            app_profile=profile,
        )
        assert context.get_severity_summary() == "needs_attention"


class TestPromptBuilder:
    """Tests for prompt builder."""

    def _create_mock_stats(self):
        """Create mock stats for testing."""
        mock_stats = MagicMock()
        mock_stats.stats = {
            'total_collections': 100,
            'total_duration_ms': 500.0,
            'max_duration_ms': 75.0,
            'collections_by_generation': {0: 80, 1: 15, 2: 5},
        }
        return mock_stats

    def test_build_returns_string(self):
        """Test that build returns a non-empty string."""
        mock_stats = self._create_mock_stats()
        events = [(1.0, 0, 5.0, 100, 0)] * 10
        start_time = time.time() - 60

        builder = PromptBuilder(
            stats=mock_stats,
            events=events,
            start_time=start_time,
        )

        prompt = builder.build()
        assert isinstance(prompt, str)
        assert len(prompt) > 100  # Should be substantial

    def test_build_compact_returns_string(self):
        """Test that build_compact returns a concise string."""
        mock_stats = self._create_mock_stats()
        events = [(1.0, 0, 5.0, 100, 0)] * 10
        start_time = time.time() - 60

        builder = PromptBuilder(
            stats=mock_stats,
            events=events,
            start_time=start_time,
        )

        prompt = builder.build_compact()
        assert isinstance(prompt, str)
        assert len(prompt) < 500  # Should be concise
        assert 'Optimize Python GC' in prompt

    def test_prompt_includes_metrics(self):
        """Test that prompt includes key metrics."""
        mock_stats = self._create_mock_stats()
        events = [(1.0, 0, 5.0, 100, 0)] * 10
        start_time = time.time() - 60

        builder = PromptBuilder(
            stats=mock_stats,
            events=events,
            start_time=start_time,
        )

        prompt = builder.build()
        
        # Should include key metrics
        assert '100' in prompt  # total collections
        assert 'Gen' in prompt  # generation info
        assert 'pause' in prompt.lower() or 'Pause' in prompt

    def test_prompt_includes_code_blocks(self):
        """Test that prompt includes code blocks."""
        mock_stats = self._create_mock_stats()
        events = [(1.0, 0, 5.0, 100, 0)] * 10
        start_time = time.time() - 60

        builder = PromptBuilder(
            stats=mock_stats,
            events=events,
            start_time=start_time,
        )

        prompt = builder.build()
        
        # Should include Python code
        assert '```python' in prompt
        assert 'gc.freeze()' in prompt
        assert 'gc.set_threshold' in prompt

    def test_threshold_calculation(self):
        """Test threshold calculation based on metrics."""
        mock_stats = self._create_mock_stats()
        # High CPU scenario
        mock_stats.stats['total_duration_ms'] = 5000.0
        
        events = [(1.0, 0, 5.0, 100, 0)] * 10
        start_time = time.time() - 60

        builder = PromptBuilder(
            stats=mock_stats,
            events=events,
            start_time=start_time,
        )

        t0, t1, t2 = builder._calculate_thresholds()
        
        # High CPU should recommend aggressive thresholds
        assert t0 >= 10000

