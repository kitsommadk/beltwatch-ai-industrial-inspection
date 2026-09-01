"""Inspection evidence orchestration for BeltWatch.

This service joins the hardware-agnostic camera, calibration, position, and
measurement contracts without coupling them to FastAPI or SQLite. Production
adapters can replace each provider independently.
"""

from dataclasses import dataclass
from datetime import datetime

from .calibration import CalibrationProfile, PositionProvider
from .camera import CameraProvider
from .measurement import WidthMeasurement, measure_width


@dataclass(frozen=True)
class InspectionEvidence:
    camera_id: str
    frame_sequence: int
    captured_at: datetime
    payload_ref: str
    position_ft: float
    position_source: str
    calibration_profile_id: str
    calibration_version: int
    measured_span_px: float
    width: WidthMeasurement


class EvidenceService:
    """Build traceable dimensional evidence from swappable providers."""

    def __init__(
        self,
        camera: CameraProvider,
        position: PositionProvider,
        calibration: CalibrationProfile,
    ) -> None:
        self.camera = camera
        self.position = position
        self.calibration = calibration

    def capture_width(
        self,
        measured_span_px: float,
        target_width_in: float,
        warning_tolerance_in: float,
        fail_tolerance_in: float,
    ) -> InspectionEvidence:
        frame = self.camera.capture()
        if frame.camera_id != self.calibration.camera_id:
            raise ValueError("camera and calibration profile do not match")

        position = self.position.sample()
        width = measure_width(
            measured_span_px=measured_span_px,
            target_width_in=target_width_in,
            calibration=self.calibration,
            warning_tolerance_in=warning_tolerance_in,
            fail_tolerance_in=fail_tolerance_in,
        )

        return InspectionEvidence(
            camera_id=frame.camera_id,
            frame_sequence=frame.sequence,
            captured_at=frame.captured_at,
            payload_ref=frame.payload_ref,
            position_ft=position.position_ft,
            position_source=position.source,
            calibration_profile_id=self.calibration.profile_id,
            calibration_version=self.calibration.version,
            measured_span_px=measured_span_px,
            width=width,
        )
