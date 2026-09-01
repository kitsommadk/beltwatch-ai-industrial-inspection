from datetime import datetime, timezone

import pytest

from app.camera import FramePacket
from app.edge_span import DarkScanlineEstimator, MultiRowDarkEstimator
from app.span_benchmark import SpanBenchmarkCase, benchmark_span_estimator


def fixture(width=1200, height=100, left=120, belt_width=960, background=220, belt=40):
    image = [[background for _ in range(width)] for _ in range(height)]
    for y in range(height):
        for x in range(left, left + belt_width):
            image[y][x] = belt
    return image


def frame(image, sequence=1):
    return FramePacket(
        camera_id="top",
        sequence=sequence,
        captured_at=datetime.now(timezone.utc),
        width_px=len(image[0]),
        height_px=len(image),
        payload_ref=f"fixture://multirow/{sequence}",
        payload=image,
    )


def test_multirow_estimator_returns_exact_geometry_on_clean_fixture():
    estimator = MultiRowDarkEstimator(threshold=100, min_run_px=100)
    span = estimator.estimate(frame(fixture()))

    assert span.left_x == 120
    assert span.right_x_exclusive == 1080
    assert span.span_px == 960
    assert span.sampled_rows == 5
    assert span.span_spread_px == 0


def test_multirow_estimator_ignores_one_corrupted_scanline():
    image = fixture()
    corrupted_y = int(round((len(image) - 1) * 0.5))
    for x in range(120, 1080):
        image[corrupted_y][x] = 220

    estimator = MultiRowDarkEstimator(threshold=100, min_run_px=100, min_valid_rows=3)
    span = estimator.estimate(frame(image))

    assert span.span_px == 960
    assert span.sampled_rows == 4


def test_multirow_estimator_rejects_large_cross_row_geometry_spread():
    image = fixture()
    row_y = int(round((len(image) - 1) * 0.25))
    for x in range(120, 1080):
        image[row_y][x] = 220
    for x in range(180, 1020):
        image[row_y][x] = 40

    estimator = MultiRowDarkEstimator(
        threshold=100,
        min_run_px=100,
        max_span_spread_px=20,
    )
    with pytest.raises(ValueError, match="inconsistent across rows"):
        estimator.estimate(frame(image))


def test_benchmark_reports_exact_matches_and_pixel_error():
    cases = [
        SpanBenchmarkCase("nominal", frame(fixture(), 1), 120, 1080),
        SpanBenchmarkCase("narrow", frame(fixture(left=121, belt_width=958), 2), 121, 1079),
        SpanBenchmarkCase("shifted", frame(fixture(left=145, belt_width=940), 3), 145, 1085),
    ]

    result = benchmark_span_estimator(
        MultiRowDarkEstimator(threshold=100, min_run_px=100),
        cases,
    )

    assert result.cases == 3
    assert result.successes == 3
    assert result.failures == 0
    assert result.exact_matches == 3
    assert result.exact_match_rate == 1.0
    assert result.mean_absolute_span_error_px == 0
    assert result.max_absolute_span_error_px == 0
    assert result.mean_edge_error_px == 0
    assert result.mean_latency_ms >= 0


def test_benchmark_counts_estimator_failure_without_hiding_it():
    blank = [[220 for _ in range(1200)] for _ in range(100)]
    cases = [
        SpanBenchmarkCase("valid", frame(fixture(), 1), 120, 1080),
        SpanBenchmarkCase("missing-belt", frame(blank, 2), 120, 1080),
    ]

    result = benchmark_span_estimator(
        DarkScanlineEstimator(threshold=100, min_run_px=100),
        cases,
    )

    assert result.cases == 2
    assert result.successes == 1
    assert result.failures == 1
    assert result.success_rate == 0.5
