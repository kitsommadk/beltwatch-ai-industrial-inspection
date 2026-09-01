from app.camera_health import runtime_camera_health
from app.runtime import build_runtime


def test_runtime_camera_health_reports_both_simulated_sources():
    runtime = build_runtime("simulation")

    records = runtime_camera_health(runtime)

    assert [record["camera_id"] for record in records] == ["bottom", "top"]
    assert all(record["status"] == "healthy" for record in records)
    assert all(record["connected"] is True for record in records)
    assert all(record["frames_captured"] == 0 for record in records)
    assert all(record["capture_failures"] == 0 for record in records)


def test_runtime_camera_health_surfaces_disconnect_and_capture_failure():
    runtime = build_runtime("simulation")
    camera = runtime.service_for("top").camera
    camera.disconnect()

    try:
        camera.capture()
    except RuntimeError:
        pass

    top = next(record for record in runtime_camera_health(runtime) if record["camera_id"] == "top")

    assert top["status"] == "disconnected"
    assert top["connected"] is False
    assert top["capture_failures"] == 1
