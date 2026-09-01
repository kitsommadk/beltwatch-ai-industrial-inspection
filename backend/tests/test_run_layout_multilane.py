from app.camera import FramePacket
from app.multilane_span import TwoLaneDarkEstimator, estimate_two_dark_belts
from app.run_layout import RunLayout, lanes_for_layout


def _image(width=120, height=40):
    image = [[220 for _ in range(width)] for _ in range(height)]
    for y in range(height):
        for x in range(10, 45):
            image[y][x] = 40
        for x in range(70, 110):
            image[y][x] = 40
    return image


def test_single_layout_has_one_generic_belt_lane():
    lanes = lanes_for_layout(RunLayout.SINGLE)
    assert [lane.lane_id for lane in lanes] == ["belt"]


def test_slit_layout_has_two_named_lanes():
    lanes = lanes_for_layout(RunLayout.SLIT_TWO_LANE)
    assert [lane.lane_id for lane in lanes] == ["belt-a", "belt-b"]


def test_two_lane_estimator_finds_both_belts_independently():
    result = estimate_two_dark_belts(_image(), threshold=100, min_run_px=20)
    assert len(result.lanes) == 2
    assert result.lanes[0].lane_id == "belt-a"
    assert result.lanes[0].span.left_x == 10
    assert result.lanes[0].span.right_x_exclusive == 45
    assert result.lanes[0].span.span_px == 35
    assert result.lanes[1].lane_id == "belt-b"
    assert result.lanes[1].span.left_x == 70
    assert result.lanes[1].span.right_x_exclusive == 110
    assert result.lanes[1].span.span_px == 40


def test_two_lane_estimator_fails_closed_when_only_one_belt_present():
    image = [[220 for _ in range(120)] for _ in range(40)]
    for y in range(40):
        for x in range(20, 90):
            image[y][x] = 40
    try:
        estimate_two_dark_belts(image, threshold=100, min_run_px=20)
        assert False, "two-lane mode must not silently accept one belt"
    except ValueError as exc:
        assert "expected exactly two" in str(exc)


def test_provider_preserves_left_to_right_identity_convention():
    frame = FramePacket(
        camera_id="top",
        sequence=1,
        captured_at=__import__("datetime").datetime.now(),
        width_px=120,
        height_px=40,
        payload_ref="generated://two-lane",
        payload=_image(),
    )
    result = TwoLaneDarkEstimator().estimate(frame)
    assert result.lanes[0].lane_id == "belt-a"
    assert result.lanes[1].lane_id == "belt-b"
