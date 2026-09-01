from pathlib import Path

from app.calibration import SimulatedPositionProvider, make_calibration_profile
from app.camera import SimulatedCamera
from app.database import initialize
from app.evidence import EvidenceService
from app.evidence_store import evidence_summary, initialize_evidence_store, list_evidence, save_evidence


def _service():
    calibration = make_calibration_profile(
        profile_id="top-cal-v1",
        camera_id="top",
        version=1,
        observed_reference_width_px=960,
        reference_width_in=48,
    )
    return EvidenceService(
        camera=SimulatedCamera("top"),
        position=SimulatedPositionProvider(start_ft=100, step_ft=5),
        calibration=calibration,
    )


def test_persist_and_summarize_evidence(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(tmp_path / "test.db"))
    initialize()
    initialize_evidence_store()

    from app.database import connect
    with connect() as con:
        cursor = con.execute(
            """INSERT INTO sessions(roll_number, work_order, operator, target_width_in,
            tolerance_in, target_length_ft, footage_ft, current_width_in, status, updated_at)
            VALUES ('R1','WO1','tester',48,0.1,1000,0,48,'inspecting','now')"""
        )
        session_id = cursor.lastrowid

    service = _service()
    first = service.capture_width(960, 48, 0.10, 0.20)
    second = service.capture_width(956, 48, 0.10, 0.20)
    save_evidence(session_id, first)
    save_evidence(session_id, second)

    rows = list_evidence(session_id)
    assert len(rows) == 2
    assert rows[0]["position_ft"] == 105
    assert rows[0]["frame_sequence"] == 2
    assert rows[1]["calibration_profile_id"] == "top-cal-v1"

    summary = evidence_summary(session_id)
    assert summary["total"] == 2
    assert summary["pass"] == 1
    assert summary["warning"] == 1
    assert summary["fail"] == 0
    assert summary["min_width_in"] == 47.8
    assert summary["max_width_in"] == 48.0


def test_duplicate_frame_is_rejected(monkeypatch, tmp_path: Path):
    import sqlite3

    monkeypatch.setenv("BELTWATCH_DB_PATH", str(tmp_path / "test.db"))
    initialize()
    initialize_evidence_store()

    from app.database import connect
    with connect() as con:
        cursor = con.execute(
            """INSERT INTO sessions(roll_number, work_order, operator, target_width_in,
            tolerance_in, target_length_ft, footage_ft, current_width_in, status, updated_at)
            VALUES ('R1','WO1','tester',48,0.1,1000,0,48,'inspecting','now')"""
        )
        session_id = cursor.lastrowid

    evidence = _service().capture_width(960, 48, 0.10, 0.20)
    save_evidence(session_id, evidence)
    try:
        save_evidence(session_id, evidence)
        assert False, "duplicate evidence should fail"
    except sqlite3.IntegrityError:
        pass
