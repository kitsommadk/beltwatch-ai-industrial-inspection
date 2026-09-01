from app.camera import FramePacket
from app.edge_span import MultiRowDarkEstimator
from app.geometry_quality import GeometryQualityPolicy, GeometryQualityStatus, assess_geometry


def _frame(rows):
    return FramePacket(
        camera_id="top",
        sequence=1,
        captured_at=__import__("datetime").datetime.now(__import__("datetime").timezone.utc),
        width_px=len(rows[0]),
        height_px=len(rows),
        payload_ref="fixture://edge-spread",
        payload=rows,
    )


def _row(width, left, right):
    return [220] * left + [40] * (right-left) + [220] * (width-right)


def test_equal_width_edges_can_still_wander_across_rows():
    width = 1200
    # Every sampled row is exactly 960 px wide, but both edges drift 8 px together.
    rows = [_row(width, 120, 1080) for _ in range(120)]
    for y, left in zip((30, 45, 60, 74, 89), (116, 118, 120, 122, 124)):
        rows[y] = _row(width, left, left + 960)

    span = MultiRowDarkEstimator(min_run_px=100).estimate(_frame(rows))
    assert span.span_spread_px == 0
    assert span.left_edge_spread_px == 8
    assert span.right_edge_spread_px == 8

    policy = GeometryQualityPolicy(
        policy_id="edge-stability-test-v1",
        high_confidence_min_rows=5,
        valid_min_rows=3,
        high_confidence_max_span_spread_px=2,
        valid_max_span_spread_px=12,
        high_confidence_max_edge_spread_px=2,
        valid_max_edge_spread_px=12,
    )
    result = assess_geometry(span, policy)
    assert result.status == GeometryQualityStatus.DEGRADED
    assert any("left_edge_spread_px=8" in reason for reason in result.reasons)
    assert any("right_edge_spread_px=8" in reason for reason in result.reasons)


def test_stable_edges_remain_high_confidence():
    rows = [_row(1200, 120, 1080) for _ in range(120)]
    span = MultiRowDarkEstimator(min_run_px=100).estimate(_frame(rows))
    policy = GeometryQualityPolicy(policy_id="stable-edge-test-v1", high_confidence_min_rows=5, valid_min_rows=3)
    assert span.left_edge_spread_px == 0
    assert span.right_edge_spread_px == 0
    assert assess_geometry(span, policy).status == GeometryQualityStatus.HIGH_CONFIDENCE
