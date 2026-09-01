"""Restart-safe temporal history queries backed by persisted inspection evidence."""

from dataclasses import dataclass

from .database import connect


@dataclass(frozen=True)
class TrustedWidthSample:
    evidence_id: int
    lane_id: str
    camera_id: str
    frame_sequence: int
    position_ft: float
    measured_width_in: float
    calibration_profile_id: str
    calibration_version: int


def trusted_width_history(
    session_id: int,
    camera_id: str,
    lane_id: str,
    calibration_profile_id: str,
    calibration_version: int,
    limit: int = 5,
) -> list[TrustedWidthSample]:
    """Return comparable recent automatic high-confidence measurements.

    Temporal comparisons are deliberately scoped by session, camera, lane, and exact
    calibration profile/version. Manual evidence is excluded because it has no
    image-derived geometry/frame-quality provenance. Results are oldest-to-newest.
    """
    if session_id < 1:
        raise ValueError("session_id must be positive")
    if not camera_id.strip():
        raise ValueError("camera_id must not be empty")
    if not lane_id.strip():
        raise ValueError("lane_id must not be empty")
    if not calibration_profile_id.strip():
        raise ValueError("calibration_profile_id must not be empty")
    if calibration_version < 1:
        raise ValueError("calibration_version must be positive")
    if limit < 1 or limit > 100:
        raise ValueError("limit must be between 1 and 100")

    with connect() as con:
        rows = con.execute(
            """SELECT e.id, e.lane_id, e.camera_id, e.frame_sequence, e.position_ft,
                      e.measured_width_in, e.calibration_profile_id, e.calibration_version
            FROM inspection_evidence e
            JOIN inspection_geometry g ON g.evidence_id=e.id
            JOIN inspection_frame_quality fq ON fq.evidence_id=e.id
            WHERE e.session_id=? AND e.camera_id=? AND e.lane_id=?
              AND e.calibration_profile_id=? AND e.calibration_version=?
              AND g.quality_status='high-confidence'
              AND fq.status='high-confidence'
            ORDER BY e.id DESC
            LIMIT ?""",
            (session_id, camera_id, lane_id, calibration_profile_id, calibration_version, limit),
        ).fetchall()

    return [
        TrustedWidthSample(
            evidence_id=row["id"],
            lane_id=row["lane_id"],
            camera_id=row["camera_id"],
            frame_sequence=row["frame_sequence"],
            position_ft=row["position_ft"],
            measured_width_in=row["measured_width_in"],
            calibration_profile_id=row["calibration_profile_id"],
            calibration_version=row["calibration_version"],
        )
        for row in reversed(rows)
    ]


def trusted_width_values(
    session_id: int,
    camera_id: str,
    lane_id: str,
    calibration_profile_id: str,
    calibration_version: int,
    limit: int = 5,
) -> list[float]:
    return [
        sample.measured_width_in
        for sample in trusted_width_history(
            session_id,
            camera_id,
            lane_id,
            calibration_profile_id,
            calibration_version,
            limit,
        )
    ]
