from datetime import datetime, timezone

from app.camera import FramePacket
from app.edge_span import MultiRowDarkEstimator
from app.geometry_quality import GeometryQualityPolicy, GeometryQualityStatus, assess_geometry


def frame(background: int, belt: int) -> FramePacket:
    width = 1200
    left = 120
    right = 1080
    row = tuple([background] * left + [belt] * (right - left) + [background] * (width - right))
    image = (row,) * 120
    return FramePacket(
        camera_id="top",
        sequence=1,
        captured_at=datetime.now(timezone.utc),
        width_px=width,
        height_px=120,
        payload_ref="fixture://contrast/1",
        payload=image,
    )


def policy() -> GeometryQualityPolicy:
    return GeometryQualityPolicy(
        policy_id="contrast-test-v1",
        high_confidence_min_rows=5,
        valid_min_rows=3,
        high_confidence_max_span_spread_px=2,
        valid_max_span_spread_px=12,
        high_confidence_max_edge_spread_px=2,
        valid_max_edge_spread_px=12,
        high_confidence_min_edge_contrast=80,
        valid_min_edge_contrast=30,
    )


def estimator() -> MultiRowDarkEstimator:
    return MultiRowDarkEstimator(threshold=100, min_run_px=100, max_span_spread_px=12)


def test_strong_visual_separation_is_high_confidence():
    span = estimator().estimate(frame(background=220, belt=40))
    assert span.min_edge_contrast == 180.0
    result = assess_geometry(span, policy())
    assert result.status == GeometryQualityStatus.HIGH_CONFIDENCE


def test_moderate_contrast_is_degraded_even_with_stable_geometry():
    span = estimator().estimate(frame(background=120, belt=80))
    assert span.span_spread_px == 0
    assert span.left_edge_spread_px == 0
    assert span.right_edge_spread_px == 0
    assert span.min_edge_contrast == 40.0
    result = assess_geometry(span, policy())
    assert result.status == GeometryQualityStatus.DEGRADED
    assert any("min_edge_contrast" in reason for reason in result.reasons)


def test_weak_contrast_is_invalid_even_when_threshold_still_finds_edges():
    span = estimator().estimate(frame(background=105, belt=95))
    assert span.min_edge_contrast == 10.0
    result = assess_geometry(span, policy())
    assert result.status == GeometryQualityStatus.INVALID
    assert any("below valid minimum" in reason for reason in result.reasons)
