"""Inspection evidence orchestration for BeltWatch."""

from dataclasses import dataclass
from datetime import datetime

from .calibration import CalibrationProfile, PositionProvider
from .camera import CameraProvider, FramePacket
from .edge_span import BeltSpan, SpanEstimator
from .geometry_quality import DEFAULT_GEOMETRY_QUALITY_POLICY, GeometryQualityError, GeometryQualityPolicy, GeometryQualityStatus, assess_geometry
from .measurement import WidthMeasurement, WidthTolerance, measure_width_from_span


@dataclass(frozen=True)
class GeometryProvenance:
    estimator_id: str
    left_x: int
    right_x_exclusive: int
    row_y: int
    threshold: float
    sampled_rows: int
    span_spread_px: int
    left_edge_spread_px: int
    right_edge_spread_px: int
    quality_policy_id: str
    quality_status: GeometryQualityStatus
    quality_reasons: tuple[str, ...]

    @classmethod
    def from_span(cls, span: BeltSpan, estimator_id: str, quality_policy: GeometryQualityPolicy) -> "GeometryProvenance":
        if not estimator_id.strip():
            raise ValueError("estimator_id must not be empty")
        quality = assess_geometry(span, quality_policy)
        return cls(
            estimator_id=estimator_id,
            left_x=span.left_x,
            right_x_exclusive=span.right_x_exclusive,
            row_y=span.row_y,
            threshold=span.threshold,
            sampled_rows=span.sampled_rows,
            span_spread_px=span.span_spread_px,
            left_edge_spread_px=span.left_edge_spread_px,
            right_edge_spread_px=span.right_edge_spread_px,
            quality_policy_id=quality.policy_id,
            quality_status=quality.status,
            quality_reasons=quality.reasons,
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
    def __init__(self, camera: CameraProvider, position: PositionProvider, calibration: CalibrationProfile) -> None:
        self.camera = camera
        self.position = position
        self.calibration = calibration

    def _build_width_evidence(self, frame: FramePacket, measured_span_px: float, target_width_in: float, warning_tolerance_in: float, fail_tolerance_in: float, geometry: GeometryProvenance | None = None) -> InspectionEvidence:
        if frame.camera_id != self.calibration.camera_id:
            raise ValueError("camera and calibration profile do not match")
        position = self.position.sample()
        width = measure_width_from_span(
            frame=frame,
            calibration=self.calibration,
            position=position,
            belt_span_px=measured_span_px,
            target_width_in=target_width_in,
            tolerance=WidthTolerance(warning_in=warning_tolerance_in, fail_in=fail_tolerance_in),
        )
        return InspectionEvidence(frame.camera_id, frame.sequence, frame.captured_at, frame.payload_ref, position.position_ft, position.source, self.calibration.profile_id, self.calibration.version, measured_span_px, width, geometry)

    def capture_width(self, measured_span_px: float, target_width_in: float, warning_tolerance_in: float, fail_tolerance_in: float) -> InspectionEvidence:
        frame = self.camera.capture()
        return self._build_width_evidence(frame, measured_span_px, target_width_in, warning_tolerance_in, fail_tolerance_in)

    def capture_width_auto(self, estimator: SpanEstimator, target_width_in: float, warning_tolerance_in: float, fail_tolerance_in: float, *, estimator_id: str | None = None, quality_policy: GeometryQualityPolicy | None = None, require_high_confidence: bool = True) -> InspectionEvidence:
        frame = self.camera.capture()
        span = estimator.estimate(frame)
        resolved_estimator_id = estimator_id or getattr(estimator, "provenance_id", None) or estimator.__class__.__name__
        resolved_quality_policy = quality_policy or getattr(estimator, "quality_policy", None) or DEFAULT_GEOMETRY_QUALITY_POLICY
        provenance = GeometryProvenance.from_span(span, resolved_estimator_id, resolved_quality_policy)
        if require_high_confidence and provenance.quality_status != GeometryQualityStatus.HIGH_CONFIDENCE:
            raise GeometryQualityError(assess_geometry(span, resolved_quality_policy))
        return self._build_width_evidence(frame, float(span.span_px), target_width_in, warning_tolerance_in, fail_tolerance_in, geometry=provenance)
