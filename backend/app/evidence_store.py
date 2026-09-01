"""SQLite persistence for traceable BeltWatch inspection evidence."""

from .database import connect
from .evidence import InspectionEvidence


EVIDENCE_SCHEMA_VERSION = 2


def initialize_evidence_store() -> None:
    """Create additive evidence tables and record the evidence-store schema version.

    Version 2 adds a one-to-one geometry-provenance table without rewriting existing
    dimensional evidence. Existing rows remain valid and simply have no geometry row.
    """
    with connect() as con:
        con.executescript(
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
            );

            CREATE TABLE IF NOT EXISTS evidence_schema_metadata (
                singleton_id INTEGER PRIMARY KEY CHECK(singleton_id = 1),
                schema_version INTEGER NOT NULL CHECK(schema_version > 0)
            );

            CREATE TABLE IF NOT EXISTS inspection_geometry (
                evidence_id INTEGER PRIMARY KEY,
                estimator_id TEXT NOT NULL,
                left_x INTEGER NOT NULL,
                right_x_exclusive INTEGER NOT NULL,
                row_y INTEGER NOT NULL,
                threshold REAL NOT NULL,
                sampled_rows INTEGER NOT NULL,
                span_spread_px INTEGER NOT NULL,
                FOREIGN KEY(evidence_id) REFERENCES inspection_evidence(id) ON DELETE CASCADE,
                CHECK(right_x_exclusive > left_x),
                CHECK(sampled_rows > 0),
                CHECK(span_spread_px >= 0)
            );

            CREATE INDEX IF NOT EXISTS idx_evidence_session_position
                ON inspection_evidence(session_id, position_ft);
            """
        )
        con.execute(
            "INSERT OR IGNORE INTO evidence_schema_metadata(singleton_id, schema_version) VALUES (1, ?)",
            (EVIDENCE_SCHEMA_VERSION,),
        )
        stored = con.execute(
            "SELECT schema_version FROM evidence_schema_metadata WHERE singleton_id=1"
        ).fetchone()[0]
        if stored != EVIDENCE_SCHEMA_VERSION:
            raise RuntimeError(
                f"evidence schema version {stored} does not match application version {EVIDENCE_SCHEMA_VERSION}; "
                "explicit evidence migration is required"
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
        evidence_id = cursor.lastrowid
        if evidence.geometry is not None:
            geometry = evidence.geometry
            con.execute(
                """
                INSERT INTO inspection_geometry(
                    evidence_id, estimator_id, left_x, right_x_exclusive, row_y,
                    threshold, sampled_rows, span_spread_px
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    evidence_id,
                    geometry.estimator_id,
                    geometry.left_x,
                    geometry.right_x_exclusive,
                    geometry.row_y,
                    geometry.threshold,
                    geometry.sampled_rows,
                    geometry.span_spread_px,
                ),
            )
        row = _evidence_row(con, evidence_id)
        return dict(row)


def _evidence_row(con, evidence_id: int):
    return con.execute(
        """
        SELECT e.*,
               g.estimator_id,
               g.left_x,
               g.right_x_exclusive,
               g.row_y AS geometry_row_y,
               g.threshold AS geometry_threshold,
               g.sampled_rows,
               g.span_spread_px
        FROM inspection_evidence e
        LEFT JOIN inspection_geometry g ON g.evidence_id=e.id
        WHERE e.id=?
        """,
        (evidence_id,),
    ).fetchone()


def list_evidence(session_id: int, limit: int = 250) -> list[dict]:
    if limit < 1 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")
    with connect() as con:
        rows = con.execute(
            """
            SELECT e.*,
                   g.estimator_id,
                   g.left_x,
                   g.right_x_exclusive,
                   g.row_y AS geometry_row_y,
                   g.threshold AS geometry_threshold,
                   g.sampled_rows,
                   g.span_spread_px
            FROM inspection_evidence e
            LEFT JOIN inspection_geometry g ON g.evidence_id=e.id
            WHERE e.session_id=?
            ORDER BY e.position_ft DESC, e.id DESC LIMIT ?
            """,
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
