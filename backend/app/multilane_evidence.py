"""Same-frame dimensional evidence for slit two-lane inspections."""

from dataclasses import dataclass

from .evidence import FrameQualityProvenance, GeometryProvenance, InspectionEvidence
from .frame_quality import DEFAULT_FRAME_QUALITY_POLICY, FrameQualityError, FrameQualityPolicy, FrameQualityStatus, assess_frame_quality
from .geometry_quality import DEFAULT_GEOMETRY_QUALITY_POLICY, GeometryQualityError, GeometryQualityPolicy, GeometryQualityStatus, assess_geometry
from .measurement import WidthTolerance, measure_width_from_span
from .multilane_span import MultiLaneSpan, TwoLaneDarkEstimator


@dataclass(frozen=True)
class LaneInspectionEvidence:
    lane_id: str
    evidence: InspectionEvidence


def capture_two_lane_width_auto(
    service,
    estimator: TwoLaneDarkEstimator,
    target_width_by_lane: dict[str, float],
    warning_tolerance_in: float,
    fail_tolerance_in: float,
    *,
    estimator_id: str | None = None,
    quality_policy: GeometryQualityPolicy | None = None,
    frame_quality_policy: FrameQualityPolicy | None = None,
    require_high_confidence: bool = True,
) -> tuple[LaneInspectionEvidence, LaneInspectionEvidence]:
    """Capture one frame and derive independent Belt A/B widths from that exact frame.

    Both lane records intentionally share frame sequence, timestamp, payload reference,
    and one sampled physical position. This prevents A/B measurements from drifting
    apart because of separate camera captures or position samples.
    """
    expected_lanes = {"belt-a", "belt-b"}
    if set(target_width_by_lane) != expected_lanes:
        raise ValueError("slit two-lane capture requires target widths for belt-a and belt-b")
    if any(width <= 0 for width in target_width_by_lane.values()):
        raise ValueError("lane target widths must be greater than zero")

    frame = service.camera.capture()
    resolved_frame_policy = frame_quality_policy or getattr(estimator, "frame_quality_policy", None) or DEFAULT_FRAME_QUALITY_POLICY
    frame_provenance = FrameQualityProvenance.from_frame(frame, resolved_frame_policy)
    if require_high_confidence and frame_provenance.status != FrameQualityStatus.HIGH_CONFIDENCE:
        raise FrameQualityError(assess_frame_quality(frame.payload, resolved_frame_policy))

    result: MultiLaneSpan = estimator.estimate(frame)
    if {lane.lane_id for lane in result.lanes} != expected_lanes:
        raise ValueError("two-lane estimator did not return belt-a and belt-b")

    position = service.position.sample()
    resolved_estimator_id = estimator_id or getattr(estimator, "provenance_id", None) or estimator.__class__.__name__
    resolved_quality_policy = quality_policy or getattr(estimator, "quality_policy", None) or DEFAULT_GEOMETRY_QUALITY_POLICY
    tolerance = WidthTolerance(warning_in=warning_tolerance_in, fail_in=fail_tolerance_in)

    captured: list[LaneInspectionEvidence] = []
    for lane in result.lanes:
        provenance = GeometryProvenance.from_span(lane.span, f"{resolved_estimator_id}:{lane.lane_id}", resolved_quality_policy)
        if require_high_confidence and provenance.quality_status != GeometryQualityStatus.HIGH_CONFIDENCE:
            raise GeometryQualityError(assess_geometry(lane.span, resolved_quality_policy))
        width = measure_width_from_span(
            frame=frame,
            calibration=service.calibration,
            position=position,
            belt_span_px=float(lane.span.span_px),
            target_width_in=target_width_by_lane[lane.lane_id],
            tolerance=tolerance,
        )
        evidence = InspectionEvidence(
            camera_id=frame.camera_id,
            frame_sequence=frame.sequence,
            captured_at=frame.captured_at,
            payload_ref=frame.payload_ref,
            position_ft=position.position_ft,
            position_source=position.source,
            calibration_profile_id=service.calibration.profile_id,
            calibration_version=service.calibration.version,
            measured_span_px=float(lane.span.span_px),
            width=width,
            geometry=provenance,
            frame_quality=frame_provenance,
        )
        captured.append(LaneInspectionEvidence(lane.lane_id, evidence))

    return captured[0], captured[1]
