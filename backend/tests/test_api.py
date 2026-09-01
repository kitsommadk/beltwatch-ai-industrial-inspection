from pathlib import Path

from fastapi.testclient import TestClient


def test_pilot_workflow(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(tmp_path / "test.db"))
    monkeypatch.setenv("BELTWATCH_INSPECTION_MODE", "simulation")

    from app.main import app, get_runtime

    get_runtime.cache_clear()
    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["mode"] == "simulation"
        assert health.json()["machine_control"] is False

        started = client.post(
            "/api/session/start",
            json={
                "roll_number": "R-DEMO-01",
                "work_order": "WO-1001",
                "operator": "Demo Operator",
                "target_width_in": 48,
                "tolerance_in": 0.08,
                "target_length_ft": 1500,
            },
        )
        assert started.status_code == 200
        assert started.json()["status"] == "inspecting"

        progress = client.post("/api/session/progress", json={"delta_ft": 25})
        assert progress.json()["footage_ft"] == 25

        event = client.post("/api/events/simulate", json={"kind": "width"})
        assert event.status_code == 200
        assert event.json()["damage_type"] == "Width deviation"
        assert event.json()["status"] == "open"

        reviewed = client.post(
            f"/api/events/{event.json()['id']}/review",
            json={"status": "acknowledged", "note": "Confirmed by operator"},
        )
        assert reviewed.json()["status"] == "acknowledged"
        assert client.get("/api/summary").json()["open_events"] == 0
        assert len(client.get("/api/audit").json()) >= 2


def test_evidence_capture_is_persisted_and_summarized(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(tmp_path / "evidence.db"))
    monkeypatch.setenv("BELTWATCH_INSPECTION_MODE", "simulation")

    from app.main import app, get_runtime

    get_runtime.cache_clear()
    with TestClient(app) as client:
        client.post(
            "/api/session/start",
            json={
                "roll_number": "R-EVIDENCE-01",
                "work_order": "WO-2001",
                "operator": "Demo Operator",
                "target_width_in": 48,
                "tolerance_in": 0.08,
                "target_length_ft": 1000,
            },
        )

        captured = client.post(
            "/api/evidence/capture",
            json={"camera": "top", "measured_span_px": 958},
        )
        assert captured.status_code == 200
        body = captured.json()
        assert body["camera_id"] == "top"
        assert body["calibration_profile_id"] == "top-simulation-v1"
        assert body["measured_width_in"] == 47.9
        assert body["status"] == "WARNING"

        records = client.get("/api/evidence").json()
        assert len(records) == 1
        assert records[0]["frame_sequence"] == 1

        summary = client.get("/api/evidence/summary").json()
        assert summary["total"] == 1
        assert summary["warning"] == 1
        assert summary["min_width_in"] == 47.9
        assert summary["max_width_in"] == 47.9


def test_evidence_requires_active_inspection(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(tmp_path / "inactive.db"))
    monkeypatch.setenv("BELTWATCH_INSPECTION_MODE", "simulation")

    from app.main import app, get_runtime

    get_runtime.cache_clear()
    with TestClient(app) as client:
        response = client.post(
            "/api/evidence/capture",
            json={"camera": "top", "measured_span_px": 960},
        )
        assert response.status_code == 409


def test_event_requires_session(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(tmp_path / "empty.db"))
    monkeypatch.setenv("BELTWATCH_INSPECTION_MODE", "simulation")

    from app.main import app, get_runtime

    get_runtime.cache_clear()
    with TestClient(app) as client:
        response = client.post("/api/events/simulate", json={"kind": "edge"})
        assert response.status_code == 409
