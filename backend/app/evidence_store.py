"""SQLite persistence for traceable BeltWatch inspection evidence."""

from .database import connect
from .evidence import InspectionEvidence


def initialize_evidence_store() -> None:
    """Create the additive evidence table without rewriting existing pilot data."""
    with connect() as con:
        con.execute(
            """
            CREATE TABLE IF NOT EXISTS inspection_evidence (
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
            )
            """
        )
        con.execute(
            "CREATE INDEX IF NOT EXISTS idx_evidence_session_position ON inspection_evidence(session_id, position_ft)"
        )


def save_evidence(session_id: int, evidence: InspectionEvidence) -> dict:
    width = evidence.width
    with connect() as con:
        cursor = con.execute(
            """
            INSERT INTO inspection_evidence(
                session_id, camera_id, frame_sequence, captured_at, payload_ref,
                position_ft, position_source, calibration_profile_id, calibration_version,
                measured_span_px, target_width_in, measured_width_in, deviation_in, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                session_id,
                evidence.camera_id,
                evidence.frame_sequence,
                evidence.captured_at.isoformat(),
                evidence.payload_ref,
                evidence.position_ft,
                evidence.position_source,
                evidence.calibration_profile_id,
                evidence.calibration_version,
                evidence.measured_span_px,
                width.target_width_in,
                width.measured_width_in,
                width.absolute_deviation_in,
                width.status.value,
            ),
        )
        row = con.execute("SELECT * FROM inspection_evidence WHERE id=?", (cursor.lastrowid,)).fetchone()
        return dict(row)


def list_evidence(session_id: int, limit: int = 250) -> list[dict]:
    if limit < 1 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")
    with connect() as con:
        rows = con.execute(
            """SELECT * FROM inspection_evidence
               WHERE session_id=? ORDER BY position_ft DESC, id DESC LIMIT ?""",
            (session_id, limit),
        ).fetchall()
        return [dict(row) for row in rows]


def evidence_summary(session_id: int) -> dict:
    with connect() as con:
        row = con.execute(
            """
            SELECT COUNT(*) total,
                   SUM(CASE WHEN status='PASS' THEN 1 ELSE 0 END) pass_count,
                   SUM(CASE WHEN status='WARNING' THEN 1 ELSE 0 END) warning_count,
                   SUM(CASE WHEN status='FAIL' THEN 1 ELSE 0 END) fail_count,
                   MIN(measured_width_in) min_width_in,
                   MAX(measured_width_in) max_width_in
            FROM inspection_evidence WHERE session_id=?
            """,
            (session_id,),
        ).fetchone()
        return {
            "total": row["total"] or 0,
            "pass": row["pass_count"] or 0,
            "warning": row["warning_count"] or 0,
            "fail": row["fail_count"] or 0,
            "min_width_in": row["min_width_in"],
            "max_width_in": row["max_width_in"],
        }
