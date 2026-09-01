import importlib
import sqlite3

import pytest
from fastapi.testclient import TestClient


def test_shared_slit_frame_has_unique_observation_identity(tmp_path, monkeypatch):
    monkeypatch.setenv("BELTWATCH_DB_PATH",str(tmp_path/"beltwatch.db")); monkeypatch.setenv("BELTWATCH_INSPECTION_MODE","replay")
    import app.main as main
    main.get_runtime.cache_clear(); importlib.reload(main)
    with TestClient(main.app) as client:
        client.post("/api/session/start",json={"roll_number":"R","work_order":"W","operator":"O","target_width_in":37.5,"tolerance_in":0.1,"target_length_ft":100,"run_layout":"slit-two-lane","lane_targets":{"belt-a":17.5,"belt-b":20.0}})
        body=client.post("/api/evidence/capture-auto",json={"camera":"top"}).json()
        records={r["lane_id"]:r for r in body["records"]}
        from app.slit_diagnostics import SlitPairDiagnostics
        from app.slit_observation_store import save_slit_observation
        d=SlitPairDiagnostics(**body["diagnostics"])
        with pytest.raises(sqlite3.IntegrityError):
            save_slit_observation(1,records["belt-a"],records["belt-b"],d)
