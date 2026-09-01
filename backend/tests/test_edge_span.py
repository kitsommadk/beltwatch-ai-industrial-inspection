from datetime import datetime, timezone

import pytest

from app.camera import FramePacket
from app.edge_span import DarkScanlineEstimator, estimate_dark_belt_span


def fixture(width=1200, height=80, left=120, belt_width=960, background=220, belt=40):
    image = [[background for _ in range(width)] for _ in range(height)]
    for y in range(height):
        for x in range(left, left + belt_width):
            image[y][x] = belt
    return image


def test_generated_fixture_returns_exact_half_open_span():
    span = estimate_dark_belt_span(fixture(), threshold=100, min_run_px=100)

    assert span.left_x == 120
    assert span.right_x_exclusive == 1080
    assert span.span_px == 960


def test_longest_dark_run_is_selected_over_small_noise():
    image = fixture()
    row = image[len(image) // 2]
    for x in range(10, 25):
        row[x] = 0

    span = estimate_dark_belt_span(image, threshold=100, min_run_px=100)
    assert span.span_px == 960


def test_missing_belt_is_rejected():
    image = [[220 for _ in range(200)] for _ in range(30)]
    with pytest.raises(ValueError, match="no belt-like dark span"):
        estimate_dark_belt_span(image, threshold=100, min_run_px=50)


def test_frame_estimator_requires_payload_and_honors_frame_contract():
    estimator = DarkScanlineEstimator(threshold=100, min_run_px=100)
    frame = FramePacket(
        camera_id="top",
        sequence=1,
        captured_at=datetime.now(timezone.utc),
        width_px=1200,
        height_px=80,
        payload_ref="fixture://belt/1",
        payload=fixture(),
    )
    span = estimator.estimate(frame)
    assert span.span_px == 960

    missing = FramePacket(
        camera_id="top",
        sequence=2,
        captured_at=datetime.now(timezone.utc),
        width_px=1200,
        height_px=80,
        payload_ref="fixture://belt/2",
    )
    with pytest.raises(ValueError, match="no image payload"):
        estimator.estimate(missing)
