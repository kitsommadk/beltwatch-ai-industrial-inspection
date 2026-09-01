import importlib

import pytest
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
        "roll_number": "ROLL-TEST",
        "work_order": "WO-TEST",
        "operator": "Replay Operator",
        "target_width_in": 48.0,
        "tolerance_in": 0.1,
        "target_length_ft": 100.0,
    }
    payload.update(updates)
    return payload


def test_single_session_persists_generic_lane_target(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        response = client.post("/api/session/start", json=_base_payload())
        assert response.status_code == 200
        assert response.json()["run_layout"] == "single"
        assert response.json()["lane_targets"] == {"belt": 48.0}


def test_slit_session_requires_exact_unequal_lane_targets(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        missing = client.post("/api/session/start", json=_base_payload(run_layout="slit-two-lane"))
        assert missing.status_code == 422

        accepted = client.post("/api/session/start", json=_base_payload(
            run_layout="slit-two-lane",
            lane_targets={"belt-a": 35.0, "belt-b": 40.0},
        ))
        assert accepted.status_code == 200
        assert accepted.json()["lane_targets"] == {"belt-a": 35.0, "belt-b": 40.0}


def test_slit_auto_capture_persists_two_lanes_from_one_frame(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        started = client.post("/api/session/start", json=_base_payload(
            run_layout="slit-two-lane",
            lane_targets={"belt-a": 17.5, "belt-b": 20.0},
        ))
        assert started.status_code == 200

        captured = client.post("/api/evidence/capture-auto", json={"camera": "top"})
        assert captured.status_code == 200, captured.text
        body = captured.json()
        assert body["run_layout"] == "slit-two-lane"
        assert len(body["records"]) == 2
        assert {record["lane_id"] for record in body["records"]} == {"belt-a", "belt-b"}
        assert len({record["frame_sequence"] for record in body["records"]}) == 1
        assert len({record["position_ft"] for record in body["records"]}) == 1
        assert body["shared_frame_sequence"] == body["records"][0]["frame_sequence"]
        assert body["shared_position_ft"] == body["records"][0]["position_ft"]

        diagnostics = body["diagnostics"]
        assert set(diagnostics) == {
            "gap_px", "belt_a_center_x_px", "belt_b_center_x_px",
            "center_distance_px", "total_occupied_span_px",
        }
        assert diagnostics["gap_px"] >= 0
        assert diagnostics["belt_a_center_x_px"] < diagnostics["belt_b_center_x_px"]
        assert diagnostics["center_distance_px"] == pytest.approx(
            diagnostics["belt_b_center_x_px"] - diagnostics["belt_a_center_x_px"]
        )
        assert diagnostics["total_occupied_span_px"] > 0

        persisted = client.get("/api/evidence").json()
        assert len(persisted) == 2
        assert {record["lane_id"] for record in persisted} == {"belt-a", "belt-b"}


def test_manual_pixel_span_capture_rejected_for_slit_session(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        client.post("/api/session/start", json=_base_payload(
            run_layout="slit-two-lane",
            lane_targets={"belt-a": 17.5, "belt-b": 20.0},
        ))
        response = client.post("/api/evidence/capture", json={"camera": "top", "measured_span_px": 350})
        assert response.status_code == 409
