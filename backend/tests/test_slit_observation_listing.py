import importlib

from fastapi.testclient import TestClient


def _start_slit(client, roll):
    return client.post("/api/session/start",json={"roll_number":roll,"work_order":"WO","operator":"O","target_width_in":37.5,"tolerance_in":0.1,"target_length_ft":100,"run_layout":"slit-two-lane","lane_targets":{"belt-a":17.5,"belt-b":20.0}})


def test_slit_observation_api_lists_only_current_session(tmp_path, monkeypatch):
    monkeypatch.setenv("BELTWATCH_DB_PATH",str(tmp_path/"beltwatch.db")); monkeypatch.setenv("BELTWATCH_INSPECTION_MODE","replay")
    import app.main as main
    main.get_runtime.cache_clear(); importlib.reload(main)
    with TestClient(main.app) as client:
        assert _start_slit(client,"R1").status_code==200
        assert client.post("/api/evidence/capture-auto",json={"camera":"top"}).status_code==200
        assert len(client.get("/api/slit-observations").json())==1
        assert _start_slit(client,"R2").status_code==200
        assert client.get("/api/slit-observations").json()==[]
