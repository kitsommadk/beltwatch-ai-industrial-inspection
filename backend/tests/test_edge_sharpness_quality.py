from app.camera import FramePacket
from app.edge_span import MultiRowDarkEstimator
from app.geometry_quality import GeometryQualityPolicy, GeometryQualityStatus, assess_geometry


def _frame(edge_values: tuple[int, ...], *, camera_id: str = "top") -> FramePacket:
    width = 120
    left = 20
    right = 100
    row = [220] * width
    row[left:right] = [40] * (right - left)
    for offset, value in enumerate(edge_values):
        row[left - 1 + offset] = value
        row[right - len(edge_values) + offset] = value
    image = tuple(tuple(row) for _ in range(20))
    return FramePacket(camera_id=camera_id, sequence=1, captured_at=None, width_px=width, height_px=20, payload_ref="generated://sharpness", payload=image)


def _symmetric_soft_frame(step: int, *, camera_id: str = "top") -> FramePacket:
    """Build stable geometry with a controlled local gradient across both edges."""
    width = 120
    left = 20
    right = 100
    row = [220] * width
    row[left:right] = [40] * (right - left)
    # Keep threshold crossing fixed while varying only the adjacent-pixel gradient.
    row[left - 2:left + 3] = [100 + 2 * step, 100 + step, 100 - step, 100 - 2 * step, 40]
    row[right - 3:right + 2] = [40, 100 - 2 * step, 100 - step, 100 + step, 100 + 2 * step]
    image = tuple(tuple(row) for _ in range(20))
    return FramePacket(camera_id=camera_id, sequence=1, captured_at=None, width_px=width, height_px=20, payload_ref="generated://sharpness", payload=image)


def _policy() -> GeometryQualityPolicy:
    return GeometryQualityPolicy(
        policy_id="sharpness-test-v1",
        high_confidence_min_rows=3,
        valid_min_rows=3,
        high_confidence_max_span_spread_px=0,
        valid_max_span_spread_px=0,
        high_confidence_max_edge_spread_px=0,
        valid_max_edge_spread_px=0,
        high_confidence_min_edge_sharpness=70.0,
        valid_min_edge_sharpness=20.0,
    )


def test_crisp_edges_are_high_confidence():
    frame = _frame((220, 40))
    span = MultiRowDarkEstimator(row_fractions=(0.25, 0.5, 0.75), threshold=100, min_run_px=20).estimate(frame)
    assert span.min_edge_sharpness == 180.0
    assert assess_geometry(span, _policy()).status == GeometryQualityStatus.HIGH_CONFIDENCE


def test_soft_edges_are_degraded_even_when_geometry_is_stable():
    frame = _symmetric_soft_frame(25)
    span = MultiRowDarkEstimator(row_fractions=(0.25, 0.5, 0.75), threshold=100, min_run_px=20).estimate(frame)
    assert span.span_spread_px == 0
    assert span.left_edge_spread_px == 0
    assert span.right_edge_spread_px == 0
    assert 20.0 <= span.min_edge_sharpness < 70.0
    assert assess_geometry(span, _policy()).status == GeometryQualityStatus.DEGRADED


def test_very_soft_edges_fail_closed():
    frame = _symmetric_soft_frame(8)
    span = MultiRowDarkEstimator(row_fractions=(0.25, 0.5, 0.75), threshold=100, min_run_px=20).estimate(frame)
    result = assess_geometry(span, _policy())
    assert span.span_spread_px == 0
    assert span.min_edge_sharpness < 20.0
    assert result.status == GeometryQualityStatus.INVALID
    assert any("sharpness" in reason for reason in result.reasons)
