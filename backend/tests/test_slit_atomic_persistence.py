import importlib

from fastapi.testclient import TestClient


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(tmp_path / "beltwatch.db"))
    monkeypatch.setenv("BELTWATCH_INSPECTION_MODE", "replay")
    import app.main as main
    main.get_runtime.cache_clear(); importlib.reload(main)
    return TestClient(main.app)


def test_slit_auto_capture_persists_complete_shared_frame_pair(tmp_path, monkeypatch):
    with _client(tmp_path, monkeypatch) as client:
        started=client.post("/api/session/start",json={
            "roll_number":"ROLL-ATOMIC","work_order":"WO-ATOMIC","operator":"Replay Operator",
            "target_width_in":37.5,"tolerance_in":0.1,"target_length_ft":100,
            "run_layout":"slit-two-lane","lane_targets":{"belt-a":17.5,"belt-b":20.0},
        })
        assert started.status_code==200
        response=client.post("/api/evidence/capture-auto",json={"camera":"top"})
        assert response.status_code==200,response.text
        body=response.json(); records=body["records"]
        assert len(records)==2
        assert {record["lane_id"] for record in records}=={"belt-a","belt-b"}
        assert {record["frame_sequence"] for record in records}=={body["shared_frame_sequence"]}
        assert {record["position_ft"] for record in records}=={body["shared_position_ft"]}
        assert {record["temporal_status"] for record in records}=={"insufficient-history"}
        persisted=client.get("/api/evidence").json()
        assert len(persisted)==2
        assert {record["lane_id"] for record in persisted}=={"belt-a","belt-b"}
        assert {record["frame_sequence"] for record in persisted}=={body["shared_frame_sequence"]}
