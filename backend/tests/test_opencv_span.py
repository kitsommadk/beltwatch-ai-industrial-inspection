from datetime import datetime, timezone

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("cv2")

from app.camera import FramePacket
from app.edge_span import MultiRowDarkEstimator
from app.opencv_span import OpenCVContourEstimator
from app.span_benchmark import SpanBenchmarkCase, benchmark_span_estimator


def fixture(width=1200, height=120, left=120, belt_width=960, background=220, belt=40):
    image = np.full((height, width), background, dtype=np.uint8)
    image[:, left : left + belt_width] = belt
    return image


def frame(image, sequence=1):
    return FramePacket(
        camera_id="top",
        sequence=sequence,
        captured_at=datetime.now(timezone.utc),
        width_px=int(image.shape[1]),
        height_px=int(image.shape[0]),
        payload_ref=f"fixture://opencv/{sequence}",
        payload=image,
    )


def test_contour_estimator_returns_exact_clean_geometry():
    span = OpenCVContourEstimator(threshold=100).estimate(frame(fixture()))
    assert span.left_x == 120
    assert span.right_x_exclusive == 1080
    assert span.span_px == 960


def test_contour_estimator_handles_shifted_narrow_belt():
    span = OpenCVContourEstimator(threshold=100).estimate(
        frame(fixture(left=145, belt_width=940))
    )
    assert span.left_x == 145
    assert span.right_x_exclusive == 1085
    assert span.span_px == 940


def test_small_dark_noise_is_not_selected_over_belt():
    image = fixture()
    image[10:20, 10:25] = 0
    span = OpenCVContourEstimator(threshold=100).estimate(frame(image))
    assert span.span_px == 960


def test_blank_image_is_rejected():
    image = np.full((120, 1200), 220, dtype=np.uint8)
    with pytest.raises(ValueError, match="no belt-like contour"):
        OpenCVContourEstimator(threshold=100).estimate(frame(image))


def test_declared_frame_dimensions_must_match_payload():
    image = fixture()
    bad = FramePacket(
        camera_id="top",
        sequence=1,
        captured_at=datetime.now(timezone.utc),
        width_px=1199,
        height_px=120,
        payload_ref="fixture://opencv/bad",
        payload=image,
    )
    with pytest.raises(ValueError, match="dimensions"):
        OpenCVContourEstimator().estimate(bad)


def test_opencv_and_multirow_share_same_benchmark_contract():
    cases = [
        SpanBenchmarkCase("nominal", frame(fixture(), 1), 120, 1080),
        SpanBenchmarkCase("narrow", frame(fixture(left=121, belt_width=958), 2), 121, 1079),
        SpanBenchmarkCase("shifted", frame(fixture(left=145, belt_width=940), 3), 145, 1085),
    ]

    contour = benchmark_span_estimator(OpenCVContourEstimator(threshold=100), cases)
    multirow = benchmark_span_estimator(
        MultiRowDarkEstimator(threshold=100, min_run_px=100), cases
    )

    assert contour.success_rate == 1.0
    assert contour.exact_match_rate == 1.0
    assert contour.mean_absolute_span_error_px == 0
    assert multirow.success_rate == 1.0
    assert multirow.exact_match_rate == 1.0
