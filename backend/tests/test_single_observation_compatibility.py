import importlib

from fastapi.testclient import TestClient


def test_single_auto_capture_does_not_create_slit_observation(tmp_path, monkeypatch):
    monkeypatch.setenv("BELTWATCH_DB_PATH",str(tmp_path/"beltwatch.db")); monkeypatch.setenv("BELTWATCH_INSPECTION_MODE","replay")
    import app.main as main
    main.get_runtime.cache_clear(); importlib.reload(main)
    with TestClient(main.app) as client:
        client.post("/api/session/start",json={"roll_number":"R","work_order":"W","operator":"O","target_width_in":48.0,"tolerance_in":0.1,"target_length_ft":100,"run_layout":"single"})
        response=client.post("/api/evidence/capture-auto",json={"camera":"top"})
        assert response.status_code==200,response.text
        assert "records" not in response.json()
        assert client.get("/api/slit-observations").json()==[]
