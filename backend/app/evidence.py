"""Inspection evidence orchestration for BeltWatch.

This service joins the hardware-agnostic camera, calibration, position, edge
geometry, and measurement contracts without coupling them to FastAPI or SQLite.
Production adapters can replace each provider independently.
"""

from dataclasses import dataclass
from datetime import datetime

from .calibration import CalibrationProfile, PositionProvider
from .camera import CameraProvider, FramePacket
from .edge_span import BeltSpan, SpanEstimator
from .measurement import WidthMeasurement, WidthTolerance, measure_width_from_span


@dataclass(frozen=True)
class GeometryProvenance:
    """Traceable image-geometry output used to produce a width measurement."""

    estimator_id: str
    left_x: int
    right_x_exclusive: int
    row_y: int
    threshold: float
    sampled_rows: int
    span_spread_px: int

    @classmethod
    def from_span(cls, span: BeltSpan, estimator_id: str) -> "GeometryProvenance":
        if not estimator_id.strip():
            raise ValueError("estimator_id must not be empty")
        return cls(
            estimator_id=estimator_id,
            left_x=span.left_x,
            right_x_exclusive=span.right_x_exclusive,
            row_y=span.row_y,
            threshold=span.threshold,
            sampled_rows=span.sampled_rows,
            span_spread_px=span.span_spread_px,
        )


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
    geometry: GeometryProvenance | None = None


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

    def _build_width_evidence(
        self,
        frame: FramePacket,
        measured_span_px: float,
        target_width_in: float,
        warning_tolerance_in: float,
        fail_tolerance_in: float,
        geometry: GeometryProvenance | None = None,
    ) -> InspectionEvidence:
        if frame.camera_id != self.calibration.camera_id:
            raise ValueError("camera and calibration profile do not match")

        position = self.position.sample()
        width = measure_width_from_span(
            frame=frame,
            calibration=self.calibration,
            position=position,
            belt_span_px=measured_span_px,
            target_width_in=target_width_in,
            tolerance=WidthTolerance(
                warning_in=warning_tolerance_in,
                fail_in=fail_tolerance_in,
            ),
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
            geometry=geometry,
        )

    def capture_width(
        self,
        measured_span_px: float,
        target_width_in: float,
        warning_tolerance_in: float,
        fail_tolerance_in: float,
    ) -> InspectionEvidence:
        """Compatibility path where upstream code supplies the measured span.

        Manual/development captures intentionally have no image-geometry provenance.
        """
        frame = self.camera.capture()
        return self._build_width_evidence(
            frame,
            measured_span_px,
            target_width_in,
            warning_tolerance_in,
            fail_tolerance_in,
        )

    def capture_width_auto(
        self,
        estimator: SpanEstimator,
        target_width_in: float,
        warning_tolerance_in: float,
        fail_tolerance_in: float,
        *,
        estimator_id: str | None = None,
    ) -> InspectionEvidence:
        """Capture one image, estimate its belt edges, and create width evidence.

        Automatic captures persist the exact left/right geometry and estimator
        provenance used for the dimensional result. Configured estimators may expose
        a stable ``provenance_id``; direct/custom estimators fall back to class name.
        """
        frame = self.camera.capture()
        span = estimator.estimate(frame)
        resolved_estimator_id = (
            estimator_id
            or getattr(estimator, "provenance_id", None)
            or estimator.__class__.__name__
        )
        provenance = GeometryProvenance.from_span(span, resolved_estimator_id)
        return self._build_width_evidence(
            frame,
            float(span.span_px),
            target_width_in,
            warning_tolerance_in,
            fail_tolerance_in,
            geometry=provenance,
        )
