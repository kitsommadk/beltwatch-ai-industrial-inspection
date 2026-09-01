"""Temporal assessment for newly captured evidence using persisted comparable history."""

from .evidence import InspectionEvidence
from .temporal_history import trusted_width_history
from .temporal_quality import TemporalQualityPolicy, TemporalQualityResult, assess_temporal_width


def assess_evidence_temporally(
    session_id: int,
    lane_id: str,
    evidence: InspectionEvidence,
    policy: TemporalQualityPolicy,
) -> TemporalQualityResult:
    """Assess evidence against trusted persisted history before the new row is saved.

    History is scoped by session, camera, lane, and exact calibration profile/version.
    Position-aware comparison uses the persisted physical position samples.
    """
    history = trusted_width_history(
        session_id=session_id,
        camera_id=evidence.camera_id,
        lane_id=lane_id,
        calibration_profile_id=evidence.calibration_profile_id,
        calibration_version=evidence.calibration_version,
        limit=policy.history_size,
    )
    return assess_temporal_width(
        evidence.width.measured_width_in,
        [sample.measured_width_in for sample in history],
        policy,
        current_position_ft=evidence.position_ft,
        history_positions_ft=[sample.position_ft for sample in history],
    )
