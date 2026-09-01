"""Runtime provider configuration for BeltWatch.

Simulation and replay are explicit operating modes. Pilot mode remains fail-closed
until physically validated hardware adapters are configured. BeltWatch must never
silently substitute simulated or replay evidence for unavailable production hardware.
"""

from dataclasses import dataclass, field
import os

from .calibration import SimulatedPositionProvider, make_calibration_profile
from .camera import SimulatedCamera
from .edge_span import MultiRowDarkEstimator, SpanEstimator
from .evidence import EvidenceService
from .frame_quality import FrameQualityPolicy
from .geometry_quality import GeometryQualityPolicy
from .multilane_span import TwoLaneDarkEstimator
from .replay import ReplayCamera, ReplayFrame


class RuntimeConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class InspectionRuntime:
    mode: str
    evidence_services: dict[str, EvidenceService]
    span_estimators: dict[str, SpanEstimator] = field(default_factory=dict)
    two_lane_services: dict[str, EvidenceService] = field(default_factory=dict)
    two_lane_estimators: dict[str, TwoLaneDarkEstimator] = field(default_factory=dict)

    def service_for(self, camera_id: str) -> EvidenceService:
        try:
            return self.evidence_services[camera_id]
        except KeyError as exc:
            raise RuntimeConfigurationError(f"camera {camera_id!r} is not configured") from exc

    def estimator_for(self, camera_id: str) -> SpanEstimator:
        try:
            return self.span_estimators[camera_id]
        except KeyError as exc:
            raise RuntimeConfigurationError(
                f"automatic span estimation is not configured for camera {camera_id!r} in {self.mode!r} mode"
            ) from exc

    def two_lane_service_for(self, camera_id: str) -> EvidenceService:
        try:
            return self.two_lane_services[camera_id]
        except KeyError as exc:
            raise RuntimeConfigurationError(
                f"two-lane capture is not configured for camera {camera_id!r} in {self.mode!r} mode"
            ) from exc

    def two_lane_estimator_for(self, camera_id: str) -> TwoLaneDarkEstimator:
        try:
            return self.two_lane_estimators[camera_id]
        except KeyError as exc:
            raise RuntimeConfigurationError(
                f"two-lane estimation is not configured for camera {camera_id!r} in {self.mode!r} mode"
            ) from exc


def _make_replay_image(*, width_px: int, height_px: int, left_x: int, span_px: int) -> tuple[tuple[int, ...], ...]:
    if width_px <= 0 or height_px <= 0 or span_px <= 0:
        raise ValueError("replay image dimensions must be greater than zero")
    right_x = left_x + span_px
    if left_x < 0 or right_x > width_px:
        raise ValueError("replay belt geometry must fit within the image")
    row = tuple([220] * left_x + [40] * span_px + [220] * (width_px - right_x))
    return (row,) * height_px


def _make_two_lane_replay_image(
    *, width_px: int, height_px: int, a_left: int, a_span: int, b_left: int, b_span: int
) -> tuple[tuple[int, ...], ...]:
    a_right = a_left + a_span
    b_right = b_left + b_span
    if not (0 <= a_left < a_right <= b_left < b_right <= width_px):
        raise ValueError("two-lane replay geometry must be ordered, non-overlapping, and fit the image")
    row = tuple(
        [220] * a_left
        + [40] * a_span
        + [220] * (b_left - a_right)
        + [40] * b_span
        + [220] * (width_px - b_right)
    )
    return (row,) * height_px


def _replay_frames(camera_id: str) -> tuple[ReplayFrame, ...]:
    spans = (960, 958, 962, 960, 956, 964)
    lefts = (120, 121, 119, 120, 122, 118)
    return tuple(
        ReplayFrame(
            source_ref=f"generated/{camera_id}/frame-{index:03d}",
            width_px=1200,
            height_px=120,
            payload=_make_replay_image(width_px=1200, height_px=120, left_x=left_x, span_px=span_px),
        )
        for index, (left_x, span_px) in enumerate(zip(lefts, spans), start=1)
    )


def _two_lane_replay_frames(camera_id: str) -> tuple[ReplayFrame, ...]:
    geometries = (
        (80, 600, 720, 360),
        (81, 598, 720, 362),
        (79, 602, 721, 358),
        (80, 600, 720, 360),
    )
    return tuple(
        ReplayFrame(
            source_ref=f"generated/{camera_id}/slit-frame-{index:03d}",
            width_px=1200,
            height_px=120,
            payload=_make_two_lane_replay_image(
                width_px=1200,
                height_px=120,
                a_left=a_left,
                a_span=a_span,
                b_left=b_left,
                b_span=b_span,
            ),
        )
        for index, (a_left, a_span, b_left, b_span) in enumerate(geometries, start=1)
    )


def _calibration(camera_id: str, mode: str):
    return make_calibration_profile(
        profile_id=f"{camera_id}-{mode}-v1",
        camera_id=camera_id,
        version=1,
        observed_reference_width_px=960.0,
        reference_width_in=48.0,
    )


def build_runtime(mode: str | None = None) -> InspectionRuntime:
    selected = (mode or os.getenv("BELTWATCH_INSPECTION_MODE", "simulation")).strip().lower()
    if selected not in {"simulation", "replay"}:
        raise RuntimeConfigurationError(
            f"inspection mode {selected!r} is not available in this build; refusing simulated fallback"
        )

    services: dict[str, EvidenceService] = {}
    estimators: dict[str, SpanEstimator] = {}
    two_lane_services: dict[str, EvidenceService] = {}
    two_lane_estimators: dict[str, TwoLaneDarkEstimator] = {}

    for camera_id in ("top", "bottom"):
        position = SimulatedPositionProvider(start_ft=0.0, step_ft=1.0)
        calibration = _calibration(camera_id, selected)
        if selected == "simulation":
            camera = SimulatedCamera(camera_id)
        else:
            camera = ReplayCamera(camera_id, _replay_frames(camera_id), loop=False)
            estimator = MultiRowDarkEstimator(threshold=100, min_run_px=100, max_span_spread_px=12)
            estimator.provenance_id = "multirow-dark-v1"
            estimator.frame_quality_policy = FrameQualityPolicy(
                policy_id="replay-frame-quality-v1",
                high_confidence_min_dynamic_range=80.0,
                valid_min_dynamic_range=30.0,
                high_confidence_max_clipped_fraction=0.01,
                valid_max_clipped_fraction=0.10,
            )
            estimator.quality_policy = GeometryQualityPolicy(
                policy_id="replay-multirow-quality-v4",
                high_confidence_min_rows=5,
                valid_min_rows=3,
                high_confidence_max_span_spread_px=2,
                valid_max_span_spread_px=12,
                high_confidence_max_edge_spread_px=2,
                valid_max_edge_spread_px=12,
                high_confidence_min_edge_contrast=80.0,
                valid_min_edge_contrast=30.0,
                high_confidence_min_edge_sharpness=80.0,
                valid_min_edge_sharpness=25.0,
            )
            estimators[camera_id] = estimator

            slit_camera = ReplayCamera(camera_id, _two_lane_replay_frames(camera_id), loop=False)
            slit_position = SimulatedPositionProvider(start_ft=0.0, step_ft=1.0)
            slit_estimator = TwoLaneDarkEstimator(threshold=100, min_run_px=100)
            slit_estimator.provenance_id = "two-lane-dark-replay-v1"
            slit_estimator.frame_quality_policy = FrameQualityPolicy(
                policy_id="replay-slit-frame-quality-v1",
                high_confidence_min_dynamic_range=80.0,
                valid_min_dynamic_range=30.0,
                high_confidence_max_clipped_fraction=0.01,
                valid_max_clipped_fraction=0.10,
            )
            slit_estimator.quality_policy = GeometryQualityPolicy(
                policy_id="replay-slit-quality-v1",
                high_confidence_min_rows=1,
                valid_min_rows=1,
                high_confidence_max_span_spread_px=0,
                valid_max_span_spread_px=0,
                high_confidence_max_edge_spread_px=0,
                valid_max_edge_spread_px=0,
                high_confidence_min_edge_contrast=80.0,
                valid_min_edge_contrast=30.0,
                high_confidence_min_edge_sharpness=80.0,
                valid_min_edge_sharpness=25.0,
            )
            two_lane_services[camera_id] = EvidenceService(slit_camera, slit_position, calibration)
            two_lane_estimators[camera_id] = slit_estimator

        services[camera_id] = EvidenceService(camera, position, calibration)

    return InspectionRuntime(
        mode=selected,
        evidence_services=services,
        span_estimators=estimators,
        two_lane_services=two_lane_services,
        two_lane_estimators=two_lane_estimators,
    )
