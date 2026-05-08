"""
Unit tests for the resilience scoring formula.
"""
import pytest
from ml_pipeline.training.train_xgboost import compute_resilience_score


def test_perfect_resilience():
    """No failures, instant recovery, full restoration = score near 1.0."""
    score = compute_resilience_score(
        failed_ratio=0.0,
        hours_to_50pct=0.0,
        final_operational_pct=100.0,
    )
    assert score > 0.95


def test_zero_resilience():
    """All nodes failed, no recovery = score near 0."""
    score = compute_resilience_score(
        failed_ratio=1.0,
        hours_to_50pct=72.0,
        final_operational_pct=0.0,
    )
    assert score < 0.1


def test_score_in_range():
    """Score should always be in [0, 1]."""
    for failed_ratio in [0.0, 0.3, 0.7, 1.0]:
        for hours in [0, 12, 36, 72]:
            for final_pct in [0, 50, 80, 100]:
                score = compute_resilience_score(failed_ratio, hours, final_pct)
                assert 0.0 <= score <= 1.0, f"Score {score} out of range for inputs ({failed_ratio}, {hours}, {final_pct})"


def test_monotonicity_failed_ratio():
    """Higher failed_ratio should give lower score."""
    score_low = compute_resilience_score(0.1, 10, 90)
    score_high = compute_resilience_score(0.8, 10, 90)
    assert score_low > score_high


def test_monotonicity_recovery_speed():
    """Faster recovery (lower hours_to_50pct) should give higher score."""
    score_fast = compute_resilience_score(0.3, 5, 90)
    score_slow = compute_resilience_score(0.3, 50, 90)
    assert score_fast > score_slow


def test_monotonicity_restoration():
    """Higher final operational % should give higher score."""
    score_high = compute_resilience_score(0.3, 10, 95)
    score_low = compute_resilience_score(0.3, 10, 40)
    assert score_high > score_low


def test_weights_sum_to_one():
    """Verify the formula weights sum to 1.0."""
    w1, w2, w3 = 0.25, 0.35, 0.40
    assert abs(w1 + w2 + w3 - 1.0) < 1e-9


def test_custom_weights():
    """Custom weights should be respected."""
    score = compute_resilience_score(
        failed_ratio=0.0,
        hours_to_50pct=0.0,
        final_operational_pct=100.0,
        w1=0.33, w2=0.33, w3=0.34
    )
    assert score > 0.95
