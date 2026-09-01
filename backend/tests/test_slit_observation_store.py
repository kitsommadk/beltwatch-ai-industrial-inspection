import importlib

from fastapi.testclient import TestClient


def test_slit_auto_capture_persists_shared_observation(tmp_path, monkeypatch):
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(tmp_path / "beltwatch.db"))
    monkeypatch.setenv("BELTWATCH_INSPECTION_MODE", "replay")
    import app.main as main
    main.get_runtime.cache_clear()
    importlib.reload(main)

    with TestClient(main.app) as client:
        started = client.post("/api/session/start", json={
            "roll_number":"ROLL-OBS","work_order":"WO-OBS","operator":"Replay Operator",
            "target_width_in":37.5,"tolerance_in":0.1,"target_length_ft":100,
            "run_layout":"slit-two-lane","lane_targets":{"belt-a":17.5,"belt-b":20.0},
        })
        assert started.status_code == 200
        captured = client.post("/api/evidence/capture-auto", json={"camera":"top"})
        assert captured.status_code == 200, captured.text
        body = captured.json()
        assert body["observation_id"] > 0

        observations = client.get("/api/slit-observations").json()
        assert len(observations) == 1
        observation = observations[0]
        records = {record["lane_id"]: record for record in body["records"]}
        assert observation["id"] == body["observation_id"]
        assert observation["belt_a_evidence_id"] == records["belt-a"]["id"]
        assert observation["belt_b_evidence_id"] == records["belt-b"]["id"]
        assert observation["camera_id"] == "top"
        assert observation["frame_sequence"] == body["shared_frame_sequence"]
        assert observation["position_ft"] == body["shared_position_ft"]
        assert observation["gap_px"] == body["diagnostics"]["gap_px"]
        assert observation["belt_a_center_x_px"] == body["diagnostics"]["belt_a_center_x_px"]
        assert observation["belt_b_center_x_px"] == body["diagnostics"]["belt_b_center_x_px"]
        assert observation["center_distance_px"] == body["diagnostics"]["center_distance_px"]
        assert observation["total_occupied_span_px"] == body["diagnostics"]["total_occupied_span_px"]


def test_slit_observation_store_rejects_mismatched_shared_frame(tmp_path, monkeypatch):
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(tmp_path / "beltwatch.db"))
    from app.database import initialize
    from app.evidence_store import initialize_evidence_store
    from app.slit_diagnostics import SlitPairDiagnostics
    from app.slit_observation_store import initialize_slit_observation_store, save_slit_observation
    initialize(); initialize_evidence_store(); initialize_slit_observation_store()

    a={"id":1,"lane_id":"belt-a","camera_id":"top","frame_sequence":10,"position_ft":5.0}
    b={"id":2,"lane_id":"belt-b","camera_id":"top","frame_sequence":11,"position_ft":5.0}
    diagnostics=SlitPairDiagnostics(5,20.0,50.0,30.0,60)
    import pytest
    with pytest.raises(ValueError, match="frame_sequence"):
        save_slit_observation(1,a,b,diagnostics)
