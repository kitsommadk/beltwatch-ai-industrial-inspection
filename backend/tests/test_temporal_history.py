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


def _insert(
    session_id: int,
    sequence: int,
    width: float,
    *,
    camera_id: str = "top",
    lane_id: str = "belt",
    calibration_profile_id: str = "cal",
    calibration_version: int = 1,
    geometry_status: str | None = "high-confidence",
    frame_status: str | None = "high-confidence",
) -> int:
    with connect() as con:
        cursor = con.execute(
            """INSERT INTO inspection_evidence(session_id,camera_id,frame_sequence,lane_id,captured_at,payload_ref,
            position_ft,position_source,calibration_profile_id,calibration_version,measured_span_px,
            target_width_in,measured_width_in,deviation_in,status)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (session_id,camera_id,sequence,lane_id,"2026-09-01T12:00:00",f"replay://{sequence}",float(sequence),"simulated",calibration_profile_id,calibration_version,960,48,width,abs(width-48),"PASS"),
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


def _history(session_id: int, *, camera_id: str = "top", lane_id: str = "belt", profile: str = "cal", version: int = 1, limit: int = 5):
    return trusted_width_history(session_id, camera_id, lane_id, profile, version, limit)


def test_history_uses_only_persisted_high_confidence_automatic_evidence(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(tmp_path / "test.db"))
    initialize(); initialize_evidence_store()
    session_id = _session()
    _insert(session_id, 1, 48.00)
    _insert(session_id, 2, 48.02, geometry_status="degraded")
    _insert(session_id, 3, 48.03, frame_status="degraded")
    _insert(session_id, 4, 48.04, geometry_status=None, frame_status=None)
    _insert(session_id, 5, 48.05)

    history = _history(session_id)
    assert [sample.frame_sequence for sample in history] == [1, 5]
    assert trusted_width_values(session_id, "top", "belt", "cal", 1, 5) == [48.00, 48.05]


def test_history_is_scoped_by_camera_lane_and_calibration(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(tmp_path / "test.db"))
    initialize(); initialize_evidence_store()
    session_id = _session()
    _insert(session_id, 1, 48.00, camera_id="top", lane_id="belt-a", calibration_profile_id="cal-a", calibration_version=1)
    _insert(session_id, 2, 47.90, camera_id="bottom", lane_id="belt-a", calibration_profile_id="cal-a", calibration_version=1)
    _insert(session_id, 3, 39.00, camera_id="top", lane_id="belt-b", calibration_profile_id="cal-a", calibration_version=1)
    _insert(session_id, 4, 47.80, camera_id="top", lane_id="belt-a", calibration_profile_id="cal-b", calibration_version=1)
    _insert(session_id, 5, 47.70, camera_id="top", lane_id="belt-a", calibration_profile_id="cal-a", calibration_version=2)
    _insert(session_id, 6, 48.02, camera_id="top", lane_id="belt-a", calibration_profile_id="cal-a", calibration_version=1)

    history = _history(session_id, lane_id="belt-a", profile="cal-a", version=1)
    assert [sample.frame_sequence for sample in history] == [1, 6]
    assert all(sample.lane_id == "belt-a" for sample in history)
    assert all(sample.camera_id == "top" for sample in history)
    assert all(sample.calibration_profile_id == "cal-a" and sample.calibration_version == 1 for sample in history)


def test_history_limit_is_restart_safe_database_state(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(tmp_path / "test.db"))
    initialize(); initialize_evidence_store()
    session_id = _session()
    for sequence in range(1, 8):
        _insert(session_id, sequence, 48.0 + sequence / 100)

    first_read = _history(session_id, limit=3)
    second_read = _history(session_id, limit=3)
    assert [s.frame_sequence for s in first_read] == [5, 6, 7]
    assert first_read == second_read
