"""
Unit tests for EALE metric computation functions.
All tests use plain Python objects (no database required).
"""
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from app.services.metrics_service import (
    compute_mastery,
    compute_retention,
    compute_transfer,
    compute_calibration,
    compute_topic_metrics,
)


# ─── Helpers ──────────────────────────────────────────────────────────────────

NOW = datetime(2025, 1, 15, 12, 0, 0)


def _attempt(q_id: int, correct: bool, confidence: int, days_ago: float = 0.0):
    return SimpleNamespace(
        question_id=q_id,
        is_correct=correct,
        confidence=confidence,
        created_at=NOW - timedelta(days=days_ago),
    )


# ─── Mastery ──────────────────────────────────────────────────────────────────

class TestMastery:
    def test_empty_returns_neutral(self):
        score, exp = compute_mastery([])
        assert score == 50.0
        assert "No" in exp

    def test_perfect_score(self):
        attempts = [_attempt(1, True, 8) for _ in range(5)]
        score, exp = compute_mastery(attempts)
        assert score == 100.0
        assert "strong" in exp.lower()

    def test_zero_score(self):
        attempts = [_attempt(1, False, 4) for _ in range(5)]
        score, _ = compute_mastery(attempts)
        assert score == 0.0

    def test_partial_score(self):
        attempts = [_attempt(1, True, 7), _attempt(1, False, 5), _attempt(1, True, 7), _attempt(1, False, 5)]
        score, _ = compute_mastery(attempts)
        assert score == 50.0

    def test_uses_only_last_10(self):
        # 15 attempts: 5 oldest wrong, 10 most-recent correct → mastery should be 100%
        old_wrong = [_attempt(1, False, 3, days_ago=float(i + 10)) for i in range(5)]
        recent_correct = [_attempt(1, True, 8, days_ago=float(i)) for i in range(10)]
        # Pass in chronological order; function takes last 10 → all correct
        all_attempts = old_wrong + recent_correct
        score, _ = compute_mastery(all_attempts)
        assert score == 100.0


# ─── Retention ────────────────────────────────────────────────────────────────

class TestRetention:
    def test_empty_returns_neutral(self):
        score, bins, exp = compute_retention([])
        assert score == 50.0
        assert bins == {}

    def test_single_attempt_no_retest(self):
        attempts = [_attempt(1, True, 8, days_ago=0)]
        score, bins, _ = compute_retention(attempts)
        # Only same-day bin; no "later" bins → can't compute drop
        assert 0 <= score <= 100

    def test_perfect_retention_no_drop(self):
        """Correct at day 0, day 1, day 4, day 8 — no drop."""
        attempts = [
            _attempt(1, True, 8, days_ago=8),   # first → same_day
            _attempt(1, True, 8, days_ago=7),   # +1d → day_1_3
            _attempt(1, True, 8, days_ago=4),   # +4d → day_3_7
            _attempt(1, True, 8, days_ago=0),   # +8d → week_plus
        ]
        score, bins, exp = compute_retention(attempts)
        assert score >= 90
        assert "strong" in exp.lower()

    def test_severe_retention_drop(self):
        """Correct same-day, wrong later."""
        attempts = [
            _attempt(1, True, 8, days_ago=7),   # same_day baseline ✓
            _attempt(1, False, 6, days_ago=3),  # day_1_3 ✗
            _attempt(1, False, 5, days_ago=0),  # week_plus ✗
        ]
        score, _, exp = compute_retention(attempts)
        assert score < 50
        assert "low" in exp.lower() or "drop" in exp.lower()

    def test_bin_labels_present(self):
        attempts = [
            _attempt(1, True, 8, days_ago=7),
            _attempt(1, True, 7, days_ago=6),  # +1d
            _attempt(1, True, 6, days_ago=4),  # +3d
            _attempt(1, False, 5, days_ago=0), # +7d
        ]
        _, bins, _ = compute_retention(attempts)
        assert "same_day" in bins or "day_1_3" in bins


# ─── Transfer ─────────────────────────────────────────────────────────────────

class TestTransfer:
    def test_no_variants_returns_neutral(self):
        orig = [_attempt(1, True, 8)]
        score, exp = compute_transfer(orig, [])
        assert score == 50.0
        assert "neutral" in exp.lower()

    def test_perfect_transfer(self):
        orig = [_attempt(1, True, 8) for _ in range(5)]
        var = [_attempt(2, True, 7) for _ in range(5)]
        score, exp = compute_transfer(orig, var)
        assert score == 100.0
        assert "excellent" in exp.lower()

    def test_zero_transfer(self):
        """Good originals, all variants wrong."""
        orig = [_attempt(1, True, 8) for _ in range(5)]
        var = [_attempt(2, False, 8) for _ in range(5)]
        score, exp = compute_transfer(orig, var)
        assert score == 0.0
        assert "poor" in exp.lower()

    def test_partial_transfer(self):
        orig = [_attempt(1, True, 8)] * 4   # 100% orig
        var = [_attempt(2, True, 7)] * 2 + [_attempt(2, False, 6)] * 2  # 50% var
        score, _ = compute_transfer(orig, var)
        assert abs(score - 50.0) < 1.0


# ─── Calibration ──────────────────────────────────────────────────────────────

class TestCalibration:
    def test_empty_returns_neutral(self):
        score, gap, exp, bins = compute_calibration([])
        assert score == 50.0
        assert gap == 0.0

    def test_perfectly_calibrated(self):
        """confidence 5 (50%), accuracy 50% → perfect calibration."""
        attempts = [_attempt(1, True, 5), _attempt(1, False, 5)]
        score, gap, exp, _ = compute_calibration(attempts)
        assert score >= 90
        assert "calibrated" in exp.lower()

    def test_severely_overconfident(self):
        """High confidence (9-10), always wrong."""
        attempts = [_attempt(1, False, 9) for _ in range(6)] + [_attempt(1, False, 10) for _ in range(4)]
        score, gap, exp, _ = compute_calibration(attempts)
        assert gap > 15
        assert "overconfident" in exp.lower()

    def test_underconfident(self):
        """Low confidence (2), always correct."""
        attempts = [_attempt(1, True, 2) for _ in range(10)]
        score, gap, exp, _ = compute_calibration(attempts)
        assert gap < -15
        assert "underconfident" in exp.lower()

    def test_bin_structure(self):
        attempts = [_attempt(1, True, c) for c in range(1, 11)]
        _, _, _, bins = compute_calibration(attempts)
        assert isinstance(bins, list)
        for b in bins:
            assert "bin" in b
            assert "count" in b
            assert "accuracy" in b


# ─── Composite DUS ────────────────────────────────────────────────────────────

class TestDUS:
    def test_formula_weights(self):
        """
        Manually construct a scenario where we know the exact DUS.
        mastery=80, retention=60, transfer=40, calibration=70
        DUS = 0.30*80 + 0.30*60 + 0.25*40 + 0.15*70 = 24+18+10+10.5 = 62.5
        """
        from unittest.mock import patch

        with (
            patch("app.services.metrics_service.compute_mastery", return_value=(80.0, "ok")),
            patch(
                "app.services.metrics_service.compute_retention",
                return_value=(60.0, {}, "ok"),
            ),
            patch("app.services.metrics_service.compute_transfer", return_value=(40.0, "ok")),
            patch(
                "app.services.metrics_service.compute_calibration",
                return_value=(70.0, 5.0, "ok", []),
            ),
        ):
            result = compute_topic_metrics(1, "Test", {1}, {2}, [])

        assert abs(result["durable_understanding_score"] - 62.5) < 0.01
        assert result["dus_formula"].startswith("DUS = 0.30")

    def test_high_mastery_poor_transfer_low_dus(self):
        """
        Alice-like pattern: high mastery, terrible transfer.
        DUS should be significantly below mastery.
        """
        orig = [_attempt(1, True, 8) for _ in range(8)]   # mastery ~100
        var = [_attempt(2, False, 8) for _ in range(5)]   # transfer ~0
        all_a = orig + var
        result = compute_topic_metrics(1, "Test", {1}, {2}, all_a)
        assert result["mastery"] > 80
        assert result["transfer_robustness"] < 20
        assert result["durable_understanding_score"] < result["mastery"]

    def test_overconfident_low_dus(self):
        """Bob-like: high confidence, low accuracy."""
        attempts = [_attempt(1, False, 9) for _ in range(10)]
        result = compute_topic_metrics(1, "Test", {1}, set(), attempts)
        assert result["calibration"] < 30
        assert result["durable_understanding_score"] < 30
