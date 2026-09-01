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
        high_confidence_max_change_per_ft=0.05,
        valid_max_change_per_ft=0.20,
        max_comparable_position_gap_ft=10.0,
    )


def test_first_trusted_measurement_is_insufficient_history_not_high_confidence():
    result = assess_temporal_width(48.0, [], _policy())
    assert result.status == TemporalQualityStatus.INSUFFICIENT_HISTORY
    assert result.history_count == 0
    assert result.previous_width_in is None
    assert result.step_change_in is None


def test_stable_width_is_high_confidence():
    result = assess_temporal_width(48.04, [48.00, 48.02, 47.99, 48.01], _policy())
    assert result.status == TemporalQualityStatus.HIGH_CONFIDENCE
    assert result.step_change_in == pytest.approx(0.03)


def test_moderate_jump_is_degraded():
    result = assess_temporal_width(48.16, [48.00, 48.01, 48.02, 48.00], _policy())
    assert result.status == TemporalQualityStatus.DEGRADED


def test_large_jump_fails_closed():
    result = assess_temporal_width(48.40, [48.00, 48.01, 48.02, 48.00], _policy())
    assert result.status == TemporalQualityStatus.INVALID


def test_history_is_bounded_to_policy_window():
    result = assess_temporal_width(48.0, [47.0, 47.0, 48.0, 48.0, 48.0, 48.0], _policy())
    assert result.history_count == 5
    assert result.history_median_width_in == pytest.approx(48.0)


def test_position_rate_is_computed_from_physical_travel():
    result = assess_temporal_width(48.08, [48.00], _policy(), current_position_ft=12.0, history_positions_ft=[10.0])
    assert result.status == TemporalQualityStatus.HIGH_CONFIDENCE
    assert result.previous_position_ft == pytest.approx(10.0)
    assert result.position_delta_ft == pytest.approx(2.0)
    assert result.width_change_per_ft == pytest.approx(0.04)


def test_fast_width_change_per_foot_can_degrade_otherwise_small_step():
    result = assess_temporal_width(48.08, [48.00], _policy(), current_position_ft=10.5, history_positions_ft=[10.0])
    assert result.status == TemporalQualityStatus.DEGRADED
    assert result.width_change_per_ft == pytest.approx(0.16)


@pytest.mark.parametrize("current_position", [10.0, 9.5])
def test_zero_or_backward_position_is_incomparable(current_position):
    result = assess_temporal_width(48.02, [48.00], _policy(), current_position_ft=current_position, history_positions_ft=[10.0])
    assert result.status == TemporalQualityStatus.INCOMPARABLE
    assert result.width_change_per_ft is None


def test_large_position_gap_is_incomparable():
    result = assess_temporal_width(48.02, [48.00], _policy(), current_position_ft=25.0, history_positions_ft=[10.0])
    assert result.status == TemporalQualityStatus.INCOMPARABLE
    assert result.position_delta_ft == pytest.approx(15.0)


def test_incomplete_position_history_is_incomparable():
    result = assess_temporal_width(48.02, [48.00], _policy(), current_position_ft=11.0, history_positions_ft=[])
    assert result.status == TemporalQualityStatus.INCOMPARABLE


def test_policy_rejects_inverted_thresholds():
    with pytest.raises(ValueError):
        TemporalQualityPolicy(policy_id="bad", high_confidence_max_step_in=0.3, valid_max_step_in=0.2)
    with pytest.raises(ValueError):
        TemporalQualityPolicy(policy_id="bad-rate", high_confidence_max_change_per_ft=0.3, valid_max_change_per_ft=0.2)
