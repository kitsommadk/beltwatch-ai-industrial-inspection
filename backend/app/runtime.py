"""Runtime provider configuration for BeltWatch.

Simulation is an explicit operating mode. Requested non-simulated modes fail closed
until their real adapters are installed; BeltWatch must never silently substitute
simulated evidence for unavailable production hardware.
"""

from dataclasses import dataclass
import os

from .calibration import SimulatedPositionProvider, make_calibration_profile
from .camera import SimulatedCamera
from .evidence import EvidenceService


class RuntimeConfigurationError(RuntimeError):
    pass


@dataclass(frozen=True)
class InspectionRuntime:
    mode: str
    evidence_services: dict[str, EvidenceService]

    def service_for(self, camera_id: str) -> EvidenceService:
        try:
            return self.evidence_services[camera_id]
        except KeyError as exc:
            raise RuntimeConfigurationError(f"camera {camera_id!r} is not configured") from exc


def build_runtime(mode: str | None = None) -> InspectionRuntime:
    selected = (mode or os.getenv("BELTWATCH_INSPECTION_MODE", "simulation")).strip().lower()
    if selected != "simulation":
        raise RuntimeConfigurationError(
            f"inspection mode {selected!r} is not available in this build; refusing simulated fallback"
        )

    # Development calibration only: 20 px/in. Physical pilot calibration must
    # replace these profiles before dimensional results are considered validated.
    services: dict[str, EvidenceService] = {}
    for camera_id in ("top", "bottom"):
        camera = SimulatedCamera(camera_id)
        position = SimulatedPositionProvider(start_ft=0.0, step_ft=1.0)
        calibration = make_calibration_profile(
            profile_id=f"{camera_id}-simulation-v1",
            camera_id=camera_id,
            version=1,
            observed_reference_width_px=960.0,
            reference_width_in=48.0,
        )
        services[camera_id] = EvidenceService(camera, position, calibration)

    return InspectionRuntime(mode=selected, evidence_services=services)
