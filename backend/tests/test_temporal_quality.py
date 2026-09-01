import pytest

from app.temporal_quality import TemporalQualityPolicy, TemporalQualityStatus, assess_temporal_width


def _policy() -> TemporalQualityPolicy:
    return TemporalQualityPolicy(
        policy_id="temporal-test-v1",
        history_size=5,
        high_confidence_max_step_in=0.10,
        valid_max_step_in=0.25,
        high_confidence_max_median_deviation_in=0.10,
        valid_max_median_deviation_in=0.25,
    )


def test_first_trusted_measurement_initializes_baseline():
    result = assess_temporal_width(48.0, [], _policy())
    assert result.status == TemporalQualityStatus.HIGH_CONFIDENCE
    assert result.history_count == 0
    assert result.previous_width_in is None


def test_stable_width_is_high_confidence():
    result = assess_temporal_width(48.04, [48.00, 48.02, 47.99, 48.01], _policy())
    assert result.status == TemporalQualityStatus.HIGH_CONFIDENCE
    assert result.step_change_in == pytest.approx(0.03)


def test_moderate_jump_is_degraded():
    result = assess_temporal_width(48.16, [48.00, 48.01, 48.02, 48.00], _policy())
    assert result.status == TemporalQualityStatus.DEGRADED
    assert any("step_change" in reason or "median_deviation" in reason for reason in result.reasons)


def test_large_jump_fails_closed():
    result = assess_temporal_width(48.40, [48.00, 48.01, 48.02, 48.00], _policy())
    assert result.status == TemporalQualityStatus.INVALID
    assert result.step_change_in == pytest.approx(0.40)


def test_history_is_bounded_to_policy_window():
    result = assess_temporal_width(48.0, [47.0, 47.0, 48.0, 48.0, 48.0, 48.0], _policy())
    assert result.history_count == 5
    assert result.history_median_width_in == pytest.approx(48.0)


def test_policy_rejects_inverted_thresholds():
    with pytest.raises(ValueError):
        TemporalQualityPolicy(policy_id="bad", high_confidence_max_step_in=0.3, valid_max_step_in=0.2)
