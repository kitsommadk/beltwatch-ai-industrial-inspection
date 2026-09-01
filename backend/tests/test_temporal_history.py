from pathlib import Path

from app.database import connect, initialize
from app.evidence_store import initialize_evidence_store
from app.temporal_history import trusted_width_history, trusted_width_values


def _session() -> int:
    with connect() as con:
        cursor = con.execute(
            """INSERT INTO sessions(roll_number, work_order, operator, target_width_in,
            tolerance_in, target_length_ft, footage_ft, current_width_in, status, updated_at)
            VALUES ('R1','WO1','tester',48,0.1,1000,0,48,'inspecting','now')"""
        )
        return cursor.lastrowid


def _insert(session_id: int, sequence: int, width: float, *, camera_id: str = "top", geometry_status: str | None = "high-confidence", frame_status: str | None = "high-confidence") -> int:
    with connect() as con:
        cursor = con.execute(
            """INSERT INTO inspection_evidence(session_id,camera_id,frame_sequence,captured_at,payload_ref,
            position_ft,position_source,calibration_profile_id,calibration_version,measured_span_px,
            target_width_in,measured_width_in,deviation_in,status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (session_id,camera_id,sequence,"2026-09-01T12:00:00",f"replay://{sequence}",float(sequence),"simulated","cal",1,960,48,width,abs(width-48),"PASS"),
        )
        evidence_id = cursor.lastrowid
        if geometry_status is not None:
            con.execute(
                """INSERT INTO inspection_geometry(evidence_id,estimator_id,left_x,right_x_exclusive,row_y,threshold,
                sampled_rows,span_spread_px,quality_policy_id,quality_status,quality_reasons_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (evidence_id,"test",10,970,100,100,5,0,"geometry-test",geometry_status,"[]"),
            )
        if frame_status is not None:
            con.execute(
                """INSERT INTO inspection_frame_quality(evidence_id,policy_id,status,sampled_pixels,mean_intensity,
                p05_intensity,p95_intensity,dynamic_range,low_clipped_fraction,high_clipped_fraction,reasons_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (evidence_id,"frame-test",frame_status,1000,120,40,220,180,0,0,"[]"),
            )
        return evidence_id


def test_history_uses_only_persisted_high_confidence_automatic_evidence(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(tmp_path / "test.db"))
    initialize(); initialize_evidence_store()
    session_id = _session()
    _insert(session_id, 1, 48.00)
    _insert(session_id, 2, 48.02, geometry_status="degraded")
    _insert(session_id, 3, 48.03, frame_status="degraded")
    _insert(session_id, 4, 48.04, geometry_status=None, frame_status=None)  # manual evidence
    _insert(session_id, 5, 48.05)

    history = trusted_width_history(session_id, "top", limit=5)
    assert [sample.frame_sequence for sample in history] == [1, 5]
    assert trusted_width_values(session_id, "top", limit=5) == [48.00, 48.05]


def test_history_is_camera_scoped_and_oldest_to_newest(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(tmp_path / "test.db"))
    initialize(); initialize_evidence_store()
    session_id = _session()
    _insert(session_id, 1, 48.00, camera_id="top")
    _insert(session_id, 2, 47.90, camera_id="bottom")
    _insert(session_id, 3, 48.02, camera_id="top")

    history = trusted_width_history(session_id, "top", limit=2)
    assert [sample.frame_sequence for sample in history] == [1, 3]
    assert [sample.measured_width_in for sample in history] == [48.00, 48.02]


def test_history_limit_is_restart_safe_database_state(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(tmp_path / "test.db"))
    initialize(); initialize_evidence_store()
    session_id = _session()
    for sequence in range(1, 8):
        _insert(session_id, sequence, 48.0 + sequence / 100)

    first_read = trusted_width_history(session_id, "top", limit=3)
    second_read = trusted_width_history(session_id, "top", limit=3)
    assert [s.frame_sequence for s in first_read] == [5, 6, 7]
    assert first_read == second_read
