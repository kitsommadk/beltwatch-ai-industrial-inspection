import importlib
import sqlite3

import pytest
from fastapi.testclient import TestClient


def _client(tmp_path, monkeypatch):
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(tmp_path / "beltwatch.db"))
    monkeypatch.setenv("BELTWATCH_INSPECTION_MODE", "replay")
    import app.main as main
    main.get_runtime.cache_clear(); importlib.reload(main)
    return main, TestClient(main.app)


def test_slit_pair_store_rolls_back_if_second_lane_conflicts(tmp_path, monkeypatch):
    main, client = _client(tmp_path, monkeypatch)
    with client:
        response=client.post("/api/session/start",json={
            "roll_number":"ROLL-ROLLBACK","work_order":"WO-ROLLBACK","operator":"Replay Operator",
            "target_width_in":37.5,"tolerance_in":0.1,"target_length_ft":100,
            "run_layout":"slit-two-lane","lane_targets":{"belt-a":17.5,"belt-b":20.0},
        })
        assert response.status_code==200
        runtime=main.get_runtime(); service=runtime.two_lane_service_for("top"); estimator=runtime.two_lane_estimator_for("top")
        capture=main.capture_two_lane_inspection_auto(service,estimator,{"belt-a":17.5,"belt-b":20.0},0.1,0.2)
        a,b=capture.lanes
        temporal_a=main.assess_evidence_temporally(1,"belt-a",a.evidence,main.TEMPORAL_POLICY)
        temporal_b=main.assess_evidence_temporally(1,"belt-b",b.evidence,main.TEMPORAL_POLICY)
        writes=[main.EvidenceWrite(a.evidence,"belt-a",temporal_a),main.EvidenceWrite(b.evidence,"belt-a",temporal_b)]
        with pytest.raises(sqlite3.IntegrityError): main.save_evidence_batch(1,writes)
        assert client.get("/api/evidence").json()==[]
