from datetime import datetime, timezone

import pytest

from app.calibration import PositionSample, make_calibration_profile
from app.camera import FramePacket
from app.measurement import (
    WidthStatus,
    WidthTolerance,
    classify_width,
    measure_width_from_span,
)


def make_frame(camera_id: str = "top") -> FramePacket:
    return FramePacket(
        camera_id=camera_id,
        sequence=7,
        captured_at=datetime.now(timezone.utc),
        width_px=1920,
        height_px=1080,
        payload_ref="sim://top/7",
    )


def make_position() -> PositionSample:
    return PositionSample(
        position_ft=125.5,
        sampled_at=datetime.now(timezone.utc),
        source="simulated",
    )


def make_calibration(camera_id: str = "top"):
    return make_calibration_profile(
        profile_id=f"{camera_id}-cal-v1",
        camera_id=camera_id,
        version=1,
        observed_reference_width_px=960,
        reference_width_in=48.0,
    )


def test_classify_width_pass_warning_fail() -> None:
    tolerance = WidthTolerance(warning_in=0.10, fail_in=0.20)

    assert classify_width(48.05, 48.0, tolerance)[0] == WidthStatus.PASS
    assert classify_width(47.89, 48.0, tolerance)[0] == WidthStatus.WARNING
    assert classify_width(47.75, 48.0, tolerance)[0] == WidthStatus.FAIL


def test_exact_warning_boundary_is_stable() -> None:
    status, deviation = classify_width(47.9, 48.0, WidthTolerance(warning_in=0.10, fail_in=0.20))
    assert deviation == 0.1
    assert status == WidthStatus.PASS


def test_measurement_links_frame_calibration_and_position() -> None:
    measurement = measure_width_from_span(
        frame=make_frame(),
        calibration=make_calibration(),
        position=make_position(),
        belt_span_px=958,
        target_width_in=48.0,
        tolerance=WidthTolerance(warning_in=0.10, fail_in=0.20),
    )

    assert measurement.measured_width_in == 47.9
    assert measurement.absolute_deviation_in == 0.1
    assert measurement.status == WidthStatus.PASS
    assert measurement.position_ft == 125.5
    assert measurement.calibration_profile_id == "top-cal-v1"


def test_rejects_wrong_camera_calibration() -> None:
    with pytest.raises(ValueError, match="camera_id"):
        measure_width_from_span(
            frame=make_frame("top"),
            calibration=make_calibration("bottom"),
            position=make_position(),
            belt_span_px=960,
            target_width_in=48.0,
            tolerance=WidthTolerance(warning_in=0.10, fail_in=0.20),
        )


@pytest.mark.parametrize("span", [0, -1, 1921])
def test_rejects_physically_invalid_pixel_spans(span: float) -> None:
    with pytest.raises(ValueError, match="belt_span_px"):
        measure_width_from_span(
            frame=make_frame(),
            calibration=make_calibration(),
            position=make_position(),
            belt_span_px=span,
            target_width_in=48.0,
            tolerance=WidthTolerance(warning_in=0.10, fail_in=0.20),
        )
