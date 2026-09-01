import pytest

from app.frame_quality import FrameQualityPolicy, FrameQualityStatus, assess_frame_quality


def _image(background: int, belt: int, *, width: int = 120, height: int = 20) -> tuple[tuple[int, ...], ...]:
    left, right = 20, 100
    row = tuple([background] * left + [belt] * (right - left) + [background] * (width - right))
    return (row,) * height


def _policy() -> FrameQualityPolicy:
    return FrameQualityPolicy(
        policy_id="frame-quality-test-v1",
        high_confidence_min_dynamic_range=80.0,
        valid_min_dynamic_range=30.0,
        high_confidence_max_clipped_fraction=0.01,
        valid_max_clipped_fraction=0.10,
    )


def test_representative_high_dynamic_range_frame_is_high_confidence():
    result = assess_frame_quality(_image(220, 40), _policy())
    assert result.status == FrameQualityStatus.HIGH_CONFIDENCE
    assert result.metrics.dynamic_range == 180.0
    assert result.metrics.low_clipped_fraction == 0.0
    assert result.metrics.high_clipped_fraction == 0.0


def test_low_dynamic_range_frame_is_degraded_before_geometry():
    result = assess_frame_quality(_image(130, 80), _policy())
    assert result.status == FrameQualityStatus.DEGRADED
    assert result.metrics.dynamic_range == 50.0
    assert any("dynamic_range" in reason for reason in result.reasons)


def test_nearly_flat_frame_is_invalid():
    result = assess_frame_quality(_image(110, 100), _policy())
    assert result.status == FrameQualityStatus.INVALID
    assert result.metrics.dynamic_range == 10.0


def test_clipped_bright_frame_fails_closed():
    image = tuple(tuple([255] * 120) for _ in range(20))
    result = assess_frame_quality(image, _policy())
    assert result.status == FrameQualityStatus.INVALID
    assert result.metrics.high_clipped_fraction == 1.0


def test_policy_rejects_inverted_thresholds():
    with pytest.raises(ValueError):
        FrameQualityPolicy(
            policy_id="bad",
            high_confidence_min_dynamic_range=20.0,
            valid_min_dynamic_range=30.0,
        )
