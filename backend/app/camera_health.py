"""Aggregate camera-provider health without coupling it to FastAPI."""

from .runtime import InspectionRuntime


def runtime_camera_health(runtime: InspectionRuntime) -> list[dict]:
    """Return serializable health records for every configured camera provider."""
    records: list[dict] = []
    for camera_id, service in sorted(runtime.evidence_services.items()):
        health = service.camera.health()
        status = "disconnected" if not health.connected else "stale" if health.stale else "healthy"
        records.append(
            {
                "camera_id": camera_id,
                "status": status,
                "connected": health.connected,
                "stale": health.stale,
                "frames_captured": health.frames_captured,
                "capture_failures": health.capture_failures,
                "last_frame_at": health.last_frame_at.isoformat() if health.last_frame_at else None,
                "stale_after_s": health.stale_after_s,
            }
        )
    return records
