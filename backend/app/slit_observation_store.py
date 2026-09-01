"""Persistence for same-frame slit pair observations.

Pair diagnostics are deterministic pixel-space observations, not root-cause
classifications or physically qualified metrology.
"""

from .database import connect
from .slit_diagnostics import SlitPairDiagnostics


SLIT_OBSERVATION_SCHEMA_VERSION = 1


def initialize_slit_observation_store() -> None:
    with connect() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS slit_observation_schema_metadata (
                singleton_id INTEGER PRIMARY KEY CHECK(singleton_id = 1),
                schema_version INTEGER NOT NULL CHECK(schema_version > 0)
            );
            CREATE TABLE IF NOT EXISTS slit_observations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id INTEGER NOT NULL,
                camera_id TEXT NOT NULL,
                frame_sequence INTEGER NOT NULL,
                position_ft REAL NOT NULL,
                belt_a_evidence_id INTEGER NOT NULL,
                belt_b_evidence_id INTEGER NOT NULL,
                gap_px INTEGER NOT NULL CHECK(gap_px >= 0),
                belt_a_center_x_px REAL NOT NULL,
                belt_b_center_x_px REAL NOT NULL,
                center_distance_px REAL NOT NULL CHECK(center_distance_px >= 0),
                total_occupied_span_px INTEGER NOT NULL CHECK(total_occupied_span_px > 0),
                FOREIGN KEY(session_id) REFERENCES sessions(id),
                FOREIGN KEY(belt_a_evidence_id) REFERENCES inspection_evidence(id),
                FOREIGN KEY(belt_b_evidence_id) REFERENCES inspection_evidence(id),
                UNIQUE(session_id, camera_id, frame_sequence),
                CHECK(belt_a_evidence_id != belt_b_evidence_id),
                CHECK(belt_b_center_x_px >= belt_a_center_x_px)
            );
            CREATE INDEX IF NOT EXISTS idx_slit_observation_session_position
                ON slit_observations(session_id, position_ft);
            """
        )
        con.execute(
            "INSERT OR IGNORE INTO slit_observation_schema_metadata(singleton_id, schema_version) VALUES (1, ?)",
            (SLIT_OBSERVATION_SCHEMA_VERSION,),
        )
        stored = con.execute(
            "SELECT schema_version FROM slit_observation_schema_metadata WHERE singleton_id=1"
        ).fetchone()[0]
        if stored != SLIT_OBSERVATION_SCHEMA_VERSION:
            raise RuntimeError(
                f"slit observation schema version {stored} does not match application version "
                f"{SLIT_OBSERVATION_SCHEMA_VERSION}; explicit migration is required"
            )


def save_slit_observation(
    session_id: int,
    belt_a_record: dict,
    belt_b_record: dict,
    diagnostics: SlitPairDiagnostics,
) -> dict:
    if belt_a_record.get("lane_id") != "belt-a" or belt_b_record.get("lane_id") != "belt-b":
        raise ValueError("slit observation requires belt-a and belt-b evidence records")
    shared_fields = ("camera_id", "frame_sequence", "position_ft")
    for field in shared_fields:
        if belt_a_record.get(field) != belt_b_record.get(field):
            raise ValueError(f"slit observation lane records must share {field}")
    with connect() as con:
        cursor = con.execute(
            """INSERT INTO slit_observations(
                session_id,camera_id,frame_sequence,position_ft,belt_a_evidence_id,belt_b_evidence_id,
                gap_px,belt_a_center_x_px,belt_b_center_x_px,center_distance_px,total_occupied_span_px
            ) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (
                session_id,
                belt_a_record["camera_id"],
                belt_a_record["frame_sequence"],
                belt_a_record["position_ft"],
                belt_a_record["id"],
                belt_b_record["id"],
                diagnostics.gap_px,
                diagnostics.belt_a_center_x_px,
                diagnostics.belt_b_center_x_px,
                diagnostics.center_distance_px,
                diagnostics.total_occupied_span_px,
            ),
        )
        row = con.execute("SELECT * FROM slit_observations WHERE id=?", (cursor.lastrowid,)).fetchone()
        return dict(row)


def list_slit_observations(session_id: int, limit: int = 250) -> list[dict]:
    if limit < 1 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")
    with connect() as con:
        rows = con.execute(
            "SELECT * FROM slit_observations WHERE session_id=? ORDER BY position_ft DESC,id DESC LIMIT ?",
            (session_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]
