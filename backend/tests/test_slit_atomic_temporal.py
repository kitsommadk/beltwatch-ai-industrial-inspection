import importlib

from fastapi.testclient import TestClient


def test_first_shared_slit_frame_has_independent_empty_temporal_history(tmp_path, monkeypatch):
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(tmp_path / "beltwatch.db")); monkeypatch.setenv("BELTWATCH_INSPECTION_MODE", "replay")
    import app.main as main
    main.get_runtime.cache_clear(); importlib.reload(main)
    with TestClient(main.app) as client:
        client.post("/api/session/start",json={"roll_number":"R","work_order":"W","operator":"O","target_width_in":37.5,"tolerance_in":0.1,"target_length_ft":100,"run_layout":"slit-two-lane","lane_targets":{"belt-a":17.5,"belt-b":20.0}})
        response=client.post("/api/evidence/capture-auto",json={"camera":"top"})
        assert response.status_code==200,response.text
        records=response.json()["records"]
        assert {r["temporal_status"] for r in records}=={"insufficient-history"}
        assert {r["temporal_history_count"] for r in records}=={0}
