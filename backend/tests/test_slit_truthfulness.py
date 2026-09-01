import importlib

from fastapi.testclient import TestClient


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(tmp_path / "beltwatch.db"))
    monkeypatch.setenv("BELTWATCH_INSPECTION_MODE", "replay")
    import app.main as main
    main.get_runtime.cache_clear()
    importlib.reload(main)
    return TestClient(main.app)


def _base_payload(**updates):
    payload = {
        "roll_number": "ROLL-T",
        "work_order": "WO-T",
        "operator": "Replay Operator",
        "target_width_in": 48.0,
        "tolerance_in": 0.1,
        "target_length_ft": 100.0,
    }
    payload.update(updates)
    return payload


def _start_slit(client):
    response = client.post("/api/session/start", json=_base_payload(
        run_layout="slit-two-lane",
        lane_targets={"belt-a": 17.5, "belt-b": 20.0},
    ))
    assert response.status_code == 200
    return response.json()


def test_single_auto_capture_keeps_legacy_raw_record_response(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        started = client.post("/api/session/start", json=_base_payload(target_width_in=20.0))
        assert started.status_code == 200
        captured = client.post("/api/evidence/capture-auto", json={"camera": "top"})
        assert captured.status_code == 200, captured.text
        body = captured.json()
        assert body["lane_id"] == "belt"
        assert "records" not in body
        assert "run_layout" not in body


def test_slit_progress_does_not_fabricate_scalar_width(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        started = _start_slit(client)
        initial = started["current_width_in"]
        progressed = client.post("/api/session/progress", json={"delta_ft": 12.0})
        assert progressed.status_code == 200
        assert progressed.json()["footage_ft"] == 12.0
        assert progressed.json()["current_width_in"] == initial


def test_slit_auto_capture_does_not_masquerade_belt_a_as_scalar_width(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        started = _start_slit(client)
        initial = started["current_width_in"]
        captured = client.post("/api/evidence/capture-auto", json={"camera": "top"})
        assert captured.status_code == 200, captured.text
        assert len(captured.json()["records"]) == 2
        session = client.get("/api/session").json()
        assert session["current_width_in"] == initial
        assert session["current_width_in"] != captured.json()["records"][0]["measured_width_in"]


def test_slit_simulated_width_event_is_rejected_until_lane_aware(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        _start_slit(client)
        response = client.post("/api/events/simulate", json={"kind": "width", "camera": "Top"})
        assert response.status_code == 409
        assert "lane-aware" in response.json()["detail"]
