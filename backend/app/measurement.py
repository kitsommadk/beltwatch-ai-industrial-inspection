"""Calibrated dimensional measurement primitives for BeltWatch.

This module keeps dimensional inspection separate from defect-model inference.
A future edge/segmentation model can estimate belt edges in image space and pass
that span here for conversion, tolerance classification, and traceable evidence.
"""

from dataclasses import dataclass
from enum import Enum

from .calibration import CalibrationProfile, PositionSample
from .camera import FramePacket


METROLOGY_DECIMALS = 6


class WidthStatus(str, Enum):
    PASS = "PASS"
    WARNING = "WARNING"
    FAIL = "FAIL"


@dataclass(frozen=True)
class WidthTolerance:
    warning_in: float
    fail_in: float

    def __post_init__(self) -> None:
        if self.warning_in < 0 or self.fail_in < 0:
            raise ValueError("tolerances must not be negative")
        if self.fail_in < self.warning_in:
            raise ValueError("fail tolerance must be >= warning tolerance")


@dataclass(frozen=True)
class WidthMeasurement:
    camera_id: str
    frame_sequence: int
    calibration_profile_id: str
    calibration_version: int
    position_ft: float
    measured_width_in: float
    target_width_in: float
    absolute_deviation_in: float
    status: WidthStatus


def classify_width(
    measured_width_in: float,
    target_width_in: float,
    tolerance: WidthTolerance,
) -> tuple[WidthStatus, float]:
    if measured_width_in < 0 or target_width_in <= 0:
        raise ValueError("widths must be physically valid")

    # Round before comparing boundaries so binary floating-point representation
    # cannot turn an intended 0.100000 in deviation into 0.10000000000000142.
    deviation = round(abs(measured_width_in - target_width_in), METROLOGY_DECIMALS)
    if deviation <= tolerance.warning_in:
        return WidthStatus.PASS, deviation
    if deviation <= tolerance.fail_in:
        return WidthStatus.WARNING, deviation
    return WidthStatus.FAIL, deviation


def measure_width_from_span(
    *,
    frame: FramePacket,
    calibration: CalibrationProfile,
    position: PositionSample,
    belt_span_px: float,
    target_width_in: float,
    tolerance: WidthTolerance,
) -> WidthMeasurement:
    if frame.camera_id != calibration.camera_id:
        raise ValueError("frame and calibration camera_id must match")
    if belt_span_px <= 0:
        raise ValueError("belt_span_px must be greater than zero")
    if belt_span_px > frame.width_px:
        raise ValueError("belt_span_px cannot exceed the frame width")

    measured_width_in = calibration.inches_from_pixels(belt_span_px)
    status, deviation = classify_width(measured_width_in, target_width_in, tolerance)

    return WidthMeasurement(
        camera_id=frame.camera_id,
        frame_sequence=frame.sequence,
        calibration_profile_id=calibration.profile_id,
        calibration_version=calibration.version,
        position_ft=position.position_ft,
        measured_width_in=round(measured_width_in, 4),
        target_width_in=target_width_in,
        absolute_deviation_in=round(deviation, 4),
        status=status,
    )
