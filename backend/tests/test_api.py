from pathlib import Path

from fastapi.testclient import TestClient


def test_pilot_workflow(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(tmp_path / "test.db"))

    from app.main import app

    with TestClient(app) as client:
        health = client.get("/api/health")
        assert health.status_code == 200
        assert health.json()["mode"] == "simulated_pilot"
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


def test_event_requires_session(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(tmp_path / "empty.db"))

    from app.main import app

    with TestClient(app) as client:
        response = client.post("/api/events/simulate", json={"kind": "edge"})
        assert response.status_code == 409

