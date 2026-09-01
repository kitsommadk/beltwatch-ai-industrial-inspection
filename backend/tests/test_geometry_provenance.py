from app.database import connect, initialize
from app.evidence_store import initialize_evidence_store, list_evidence, save_evidence
from app.runtime import build_runtime


def _session_id():
    with connect() as con:
        cursor = con.execute(
            """INSERT INTO sessions(roll_number, work_order, operator, target_width_in,
            tolerance_in, target_length_ft, footage_ft, current_width_in, status, updated_at)
            VALUES ('R-GEO','WO-GEO','tester',48,0.1,1000,0,48,'inspecting','now')"""
        )
        return cursor.lastrowid


def test_replay_auto_capture_records_exact_geometry_and_provider(monkeypatch, tmp_path):
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(tmp_path / "geometry.db"))
    initialize()
    initialize_evidence_store()
    session_id = _session_id()

    runtime = build_runtime("replay")
    service = runtime.service_for("top")
    evidence = service.capture_width_auto(
        estimator=runtime.estimator_for("top"),
        target_width_in=48,
        warning_tolerance_in=0.1,
        fail_tolerance_in=0.2,
    )

    assert evidence.geometry is not None
    assert evidence.geometry.estimator_id == "multirow-dark-v1"
    assert evidence.geometry.left_x == 120
    assert evidence.geometry.right_x_exclusive == 1080
    assert evidence.geometry.sampled_rows == 5
    assert evidence.geometry.span_spread_px == 0

    saved = save_evidence(session_id, evidence)
    assert saved["estimator_id"] == "multirow-dark-v1"
    assert saved["left_x"] == 120
    assert saved["right_x_exclusive"] == 1080
    assert saved["sampled_rows"] == 5
    assert saved["span_spread_px"] == 0

    listed = list_evidence(session_id)
    assert listed[0]["estimator_id"] == "multirow-dark-v1"
    assert listed[0]["geometry_threshold"] == 100.0


def test_manual_capture_remains_explicitly_without_geometry(monkeypatch, tmp_path):
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(tmp_path / "manual.db"))
    initialize()
    initialize_evidence_store()
    session_id = _session_id()

    runtime = build_runtime("simulation")
    evidence = runtime.service_for("top").capture_width(960, 48, 0.1, 0.2)
    assert evidence.geometry is None

    saved = save_evidence(session_id, evidence)
    assert saved["estimator_id"] is None
    assert saved["left_x"] is None
    assert saved["right_x_exclusive"] is None


def test_geometry_row_is_removed_when_parent_evidence_is_deleted(monkeypatch, tmp_path):
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(tmp_path / "cascade.db"))
    initialize()
    initialize_evidence_store()
    session_id = _session_id()

    runtime = build_runtime("replay")
    evidence = runtime.service_for("top").capture_width_auto(
        estimator=runtime.estimator_for("top"),
        target_width_in=48,
        warning_tolerance_in=0.1,
        fail_tolerance_in=0.2,
    )
    saved = save_evidence(session_id, evidence)

    with connect() as con:
        con.execute("DELETE FROM inspection_evidence WHERE id=?", (saved["id"],))
        count = con.execute(
            "SELECT COUNT(*) FROM inspection_geometry WHERE evidence_id=?", (saved["id"],)
        ).fetchone()[0]
    assert count == 0
