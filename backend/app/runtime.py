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
from .geometry_quality import GeometryQualityPolicy
from .replay import ReplayCamera, ReplayFrame


class RuntimeConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class InspectionRuntime:
    mode: str
    evidence_services: dict[str, EvidenceService]
    span_estimators: dict[str, SpanEstimator] = field(default_factory=dict)

    def service_for(self, camera_id: str) -> EvidenceService:
        try:
            return self.evidence_services[camera_id]
        except KeyError as exc:
            raise RuntimeConfigurationError(f"camera {camera_id!r} is not configured") from exc

    def estimator_for(self, camera_id: str) -> SpanEstimator:
        try:
            return self.span_estimators[camera_id]
        except KeyError as exc:
            raise RuntimeConfigurationError(f"automatic span estimation is not configured for camera {camera_id!r} in {self.mode!r} mode") from exc


def _make_replay_image(*, width_px: int, height_px: int, left_x: int, span_px: int) -> tuple[tuple[int, ...], ...]:
    if width_px <= 0 or height_px <= 0 or span_px <= 0:
        raise ValueError("replay image dimensions must be greater than zero")
    right_x = left_x + span_px
    if left_x < 0 or right_x > width_px:
        raise ValueError("replay belt geometry must fit within the image")
    row = tuple([220] * left_x + [40] * span_px + [220] * (width_px - right_x))
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
        raise RuntimeConfigurationError(f"inspection mode {selected!r} is not available in this build; refusing simulated fallback")

    services: dict[str, EvidenceService] = {}
    estimators: dict[str, SpanEstimator] = {}
    for camera_id in ("top", "bottom"):
        position = SimulatedPositionProvider(start_ft=0.0, step_ft=1.0)
        calibration = _calibration(camera_id, selected)
        if selected == "simulation":
            camera = SimulatedCamera(camera_id)
        else:
            camera = ReplayCamera(camera_id, _replay_frames(camera_id), loop=False)
            estimator = MultiRowDarkEstimator(threshold=100, min_run_px=100, max_span_spread_px=12)
            estimator.provenance_id = "multirow-dark-v1"
            estimator.quality_policy = GeometryQualityPolicy(
                policy_id="replay-multirow-quality-v3",
                high_confidence_min_rows=5,
                valid_min_rows=3,
                high_confidence_max_span_spread_px=2,
                valid_max_span_spread_px=12,
                high_confidence_max_edge_spread_px=2,
                valid_max_edge_spread_px=12,
                high_confidence_min_edge_contrast=80.0,
                valid_min_edge_contrast=30.0,
            )
            estimators[camera_id] = estimator
        services[camera_id] = EvidenceService(camera, position, calibration)

    return InspectionRuntime(mode=selected, evidence_services=services, span_estimators=estimators)
