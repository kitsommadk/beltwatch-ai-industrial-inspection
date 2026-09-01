from pathlib import Path

from app.database import connect, initialize
from app.evidence_store import EVIDENCE_SCHEMA_VERSION, initialize_evidence_store


def test_v2_evidence_store_migrates_additively_to_current_version(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(tmp_path / "migration.db"))
    initialize()
    with connect() as con:
        session_id = con.execute(
            """INSERT INTO sessions(roll_number, work_order, operator, target_width_in,
            tolerance_in, target_length_ft, footage_ft, current_width_in, status, updated_at)
            VALUES ('R1','WO1','tester',48,0.1,1000,0,48,'inspecting','now')"""
        ).lastrowid
        con.executescript(
            """
            CREATE TABLE inspection_evidence (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                camera_id TEXT NOT NULL,
                frame_sequence INTEGER NOT NULL,
                captured_at TEXT NOT NULL,
                payload_ref TEXT NOT NULL,
                position_ft REAL NOT NULL,
                position_source TEXT NOT NULL,
                calibration_profile_id TEXT NOT NULL,
                calibration_version INTEGER NOT NULL,
                measured_span_px REAL NOT NULL,
                target_width_in REAL NOT NULL,
                measured_width_in REAL NOT NULL,
                deviation_in REAL NOT NULL,
                status TEXT NOT NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(id),
                UNIQUE(session_id, camera_id, frame_sequence)
            );
            CREATE TABLE evidence_schema_metadata (
                singleton_id INTEGER PRIMARY KEY CHECK(singleton_id = 1),
                schema_version INTEGER NOT NULL CHECK(schema_version > 0)
            );
            INSERT INTO evidence_schema_metadata(singleton_id, schema_version) VALUES (1, 2);
            CREATE TABLE inspection_geometry (
                evidence_id INTEGER PRIMARY KEY,
                estimator_id TEXT NOT NULL,
                left_x INTEGER NOT NULL,
                right_x_exclusive INTEGER NOT NULL,
                row_y INTEGER NOT NULL,
                threshold REAL NOT NULL,
                sampled_rows INTEGER NOT NULL,
                span_spread_px INTEGER NOT NULL,
                FOREIGN KEY(evidence_id) REFERENCES inspection_evidence(id) ON DELETE CASCADE
            );
            """
        )
        con.execute(
            """INSERT INTO inspection_evidence(session_id,camera_id,frame_sequence,captured_at,payload_ref,
            position_ft,position_source,calibration_profile_id,calibration_version,measured_span_px,target_width_in,
            measured_width_in,deviation_in,status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (session_id,"top",7,"2026-09-01T12:00:00","replay://legacy",125.5,"replay-position",
             "top-cal-v1",1,960,48,48,0,"PASS"),
        )

    initialize_evidence_store()

    with connect() as con:
        version = con.execute("SELECT schema_version FROM evidence_schema_metadata WHERE singleton_id=1").fetchone()[0]
        columns = {row["name"] for row in con.execute("PRAGMA table_info(inspection_geometry)")}
        evidence_columns = {row["name"] for row in con.execute("PRAGMA table_info(inspection_evidence)")}
        frame_quality_columns = {row["name"] for row in con.execute("PRAGMA table_info(inspection_frame_quality)")}
        temporal_columns = {row["name"] for row in con.execute("PRAGMA table_info(inspection_temporal_quality)")}
        migrated = con.execute("SELECT lane_id, camera_id, frame_sequence, payload_ref FROM inspection_evidence").fetchone()
        fk_issues = con.execute("PRAGMA foreign_key_check").fetchall()

    assert version == EVIDENCE_SCHEMA_VERSION == 9
    assert "lane_id" in evidence_columns
    assert migrated["lane_id"] == "belt"
    assert migrated["camera_id"] == "top"
    assert migrated["frame_sequence"] == 7
    assert migrated["payload_ref"] == "replay://legacy"
    assert {
        "quality_policy_id", "quality_status", "quality_reasons_json",
        "left_edge_spread_px", "right_edge_spread_px", "min_edge_contrast", "min_edge_sharpness",
    } <= columns
    assert {
        "policy_id", "status", "sampled_pixels", "mean_intensity", "p05_intensity", "p95_intensity",
        "dynamic_range", "low_clipped_fraction", "high_clipped_fraction", "reasons_json",
    } <= frame_quality_columns
    assert {
        "evidence_id", "policy_id", "status", "history_count", "previous_width_in",
        "history_median_width_in", "step_change_in", "median_deviation_in",
        "previous_position_ft", "position_delta_ft", "width_change_per_ft", "reasons_json",
    } <= temporal_columns
    assert fk_issues == []
