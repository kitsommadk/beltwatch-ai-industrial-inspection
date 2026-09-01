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


def test_classify_width_pass_warning_fail() -> None:
    tolerance = WidthTolerance(warning_in=0.10, fail_in=0.20)

    assert classify_width(48.05, 48.0, tolerance)[0] == WidthStatus.PASS
    assert classify_width(47.89, 48.0, tolerance)[0] == WidthStatus.WARNING
    assert classify_width(47.75, 48.0, tolerance)[0] == WidthStatus.FAIL


def test_measurement_links_frame_calibration_and_position() -> None:
    calibration = make_calibration_profile(
        profile_id="top-cal-v1",
        camera_id="top",
        version=1,
        observed_reference_width_px=960,
        reference_width_in=48.0,
    )
    position = PositionSample(
        position_ft=125.5,
        sampled_at=datetime.now(timezone.utc),
        source="simulated",
    )

    measurement = measure_width_from_span(
        frame=make_frame(),
        calibration=calibration,
        position=position,
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
    calibration = make_calibration_profile(
        profile_id="bottom-cal-v1",
        camera_id="bottom",
        version=1,
        observed_reference_width_px=960,
        reference_width_in=48.0,
    )
    position = PositionSample(
        position_ft=0,
        sampled_at=datetime.now(timezone.utc),
        source="simulated",
    )

    with pytest.raises(ValueError, match="camera_id"):
        measure_width_from_span(
            frame=make_frame("top"),
            calibration=calibration,
            position=position,
            belt_span_px=960,
            target_width_in=48.0,
            tolerance=WidthTolerance(warning_in=0.10, fail_in=0.20),
        )
