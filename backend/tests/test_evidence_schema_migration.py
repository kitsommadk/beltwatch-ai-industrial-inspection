from pathlib import Path

from app.database import connect, initialize
from app.evidence_store import EVIDENCE_SCHEMA_VERSION, initialize_evidence_store


def test_v2_evidence_store_migrates_additively_to_current_version(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(tmp_path / "migration.db"))
    initialize()
    with connect() as con:
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

    initialize_evidence_store()

    with connect() as con:
        version = con.execute(
            "SELECT schema_version FROM evidence_schema_metadata WHERE singleton_id=1"
        ).fetchone()[0]
        columns = {row["name"] for row in con.execute("PRAGMA table_info(inspection_geometry)")}

    assert version == EVIDENCE_SCHEMA_VERSION == 4
    assert {
        "quality_policy_id",
        "quality_status",
        "quality_reasons_json",
        "left_edge_spread_px",
        "right_edge_spread_px",
    } <= columns
