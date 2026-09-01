from datetime import datetime, timezone

import pytest

np = pytest.importorskip("numpy")
pytest.importorskip("cv2")

from app.camera import FramePacket
from app.cv_fixtures import make_belt_fixture
from app.edge_span import MultiRowDarkEstimator
from app.opencv_span import OpenCVContourEstimator
from app.span_benchmark import SpanBenchmarkCase, benchmark_span_estimator


def as_frame(fixture, sequence: int) -> FramePacket:
    image = fixture.image
    return FramePacket(
        camera_id="top",
        sequence=sequence,
        captured_at=datetime.now(timezone.utc),
        width_px=int(image.shape[1]),
        height_px=int(image.shape[0]),
        payload_ref=f"fixture://robustness/{fixture.label}/{sequence}",
        payload=image,
    )


def benchmark_cases():
    fixtures = [
        make_belt_fixture(label="clean"),
        make_belt_fixture(left=145, belt_width=940, label="shifted-narrow"),
        make_belt_fixture(brightness_gradient=25, label="brightness-gradient"),
        make_belt_fixture(impulse_noise_fraction=0.01, label="impulse-noise"),
        make_belt_fixture(shadow_band=(300, 520, -35), label="shadow-band"),
        make_belt_fixture(edge_notch=("left", 0, 22, 18), label="upper-left-notch"),
        make_belt_fixture(edge_notch=("right", 98, 120, 18), label="lower-right-notch"),
    ]
    return [
        SpanBenchmarkCase(
            fixture.label,
            as_frame(fixture, index),
            fixture.expected_left_x,
            fixture.expected_right_x_exclusive,
        )
        for index, fixture in enumerate(fixtures, start=1)
    ]


def test_generated_fixture_is_deterministic():
    first = make_belt_fixture(impulse_noise_fraction=0.02, seed=11)
    second = make_belt_fixture(impulse_noise_fraction=0.02, seed=11)
    assert (first.image == second.image).all()


def test_fixture_validation_rejects_impossible_geometry():
    with pytest.raises(ValueError, match="fit within"):
        make_belt_fixture(width=100, left=50, belt_width=80)


def test_sparse_impulse_noise_does_not_expand_contour_span():
    fixture = make_belt_fixture(impulse_noise_fraction=0.01, label="impulse-noise")
    span = OpenCVContourEstimator(threshold=100).estimate(as_frame(fixture, 1))

    assert span.left_x == fixture.expected_left_x
    assert span.right_x_exclusive == fixture.expected_right_x_exclusive
    assert span.span_px == fixture.expected_span_px


def test_opencv_contour_provider_meets_generated_robustness_gate():
    result = benchmark_span_estimator(OpenCVContourEstimator(threshold=100), benchmark_cases())

    assert result.success_rate == 1.0
    assert result.mean_absolute_span_error_px is not None
    assert result.mean_absolute_span_error_px <= 2.0
    assert result.max_absolute_span_error_px is not None
    assert result.max_absolute_span_error_px <= 6
    assert result.mean_edge_error_px is not None
    assert result.mean_edge_error_px <= 2.0


def test_multirow_provider_meets_generated_robustness_gate():
    result = benchmark_span_estimator(
        MultiRowDarkEstimator(threshold=100, min_run_px=100, max_span_spread_px=30),
        benchmark_cases(),
    )

    assert result.success_rate >= 6 / 7
    assert result.mean_absolute_span_error_px is not None
    assert result.mean_absolute_span_error_px <= 3.0


def test_benchmark_keeps_provider_results_independent():
    cases = benchmark_cases()
    contour = benchmark_span_estimator(OpenCVContourEstimator(threshold=100), cases)
    multirow = benchmark_span_estimator(
        MultiRowDarkEstimator(threshold=100, min_run_px=100, max_span_spread_px=30),
        cases,
    )

    assert contour.cases == multirow.cases == 7
    assert contour.successes <= contour.cases
    assert multirow.successes <= multirow.cases
