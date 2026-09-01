"""SQLite persistence for traceable BeltWatch inspection evidence."""

import json

from .database import connect
from .evidence import InspectionEvidence


EVIDENCE_SCHEMA_VERSION = 5


def _geometry_columns(con) -> set[str]:
    return {row["name"] for row in con.execute("PRAGMA table_info(inspection_geometry)").fetchall()}


def _migrate_v2_to_v3(con) -> None:
    columns = _geometry_columns(con)
    if "quality_policy_id" not in columns:
        con.execute("ALTER TABLE inspection_geometry ADD COLUMN quality_policy_id TEXT")
    if "quality_status" not in columns:
        con.execute("ALTER TABLE inspection_geometry ADD COLUMN quality_status TEXT")
    if "quality_reasons_json" not in columns:
        con.execute("ALTER TABLE inspection_geometry ADD COLUMN quality_reasons_json TEXT")
    con.execute("UPDATE evidence_schema_metadata SET schema_version=3 WHERE singleton_id=1")


def _migrate_v3_to_v4(con) -> None:
    columns = _geometry_columns(con)
    if "left_edge_spread_px" not in columns:
        con.execute("ALTER TABLE inspection_geometry ADD COLUMN left_edge_spread_px INTEGER")
    if "right_edge_spread_px" not in columns:
        con.execute("ALTER TABLE inspection_geometry ADD COLUMN right_edge_spread_px INTEGER")
    con.execute("UPDATE evidence_schema_metadata SET schema_version=4 WHERE singleton_id=1")


def _migrate_v4_to_v5(con) -> None:
    columns = _geometry_columns(con)
    if "min_edge_contrast" not in columns:
        con.execute("ALTER TABLE inspection_geometry ADD COLUMN min_edge_contrast REAL")
    con.execute("UPDATE evidence_schema_metadata SET schema_version=5 WHERE singleton_id=1")


def initialize_evidence_store() -> None:
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
                left_edge_spread_px INTEGER,
                right_edge_spread_px INTEGER,
                min_edge_contrast REAL,
                quality_policy_id TEXT,
                quality_status TEXT,
                quality_reasons_json TEXT,
                FOREIGN KEY(evidence_id) REFERENCES inspection_evidence(id) ON DELETE CASCADE,
                CHECK(right_x_exclusive > left_x),
                CHECK(sampled_rows > 0),
                CHECK(span_spread_px >= 0)
            );
            CREATE INDEX IF NOT EXISTS idx_evidence_session_position ON inspection_evidence(session_id, position_ft);
            """
        )
        con.execute("INSERT OR IGNORE INTO evidence_schema_metadata(singleton_id, schema_version) VALUES (1, ?)", (EVIDENCE_SCHEMA_VERSION,))
        stored = con.execute("SELECT schema_version FROM evidence_schema_metadata WHERE singleton_id=1").fetchone()[0]
        if stored == 2:
            _migrate_v2_to_v3(con)
            stored = 3
        if stored == 3:
            _migrate_v3_to_v4(con)
            stored = 4
        if stored == 4:
            _migrate_v4_to_v5(con)
            stored = 5
        if stored != EVIDENCE_SCHEMA_VERSION:
            raise RuntimeError(f"evidence schema version {stored} does not match application version {EVIDENCE_SCHEMA_VERSION}; explicit evidence migration is required")


def _decode_reasons(value: str | None) -> list[str] | None:
    return None if value is None else list(json.loads(value))


def _evidence_row(con, evidence_id: int):
    return con.execute(
        """SELECT e.*, g.estimator_id, g.left_x, g.right_x_exclusive,
        g.row_y AS geometry_row_y, g.threshold AS geometry_threshold, g.sampled_rows,
        g.span_spread_px, g.left_edge_spread_px, g.right_edge_spread_px, g.min_edge_contrast,
        g.quality_policy_id, g.quality_status, g.quality_reasons_json
        FROM inspection_evidence e LEFT JOIN inspection_geometry g ON g.evidence_id=e.id
        WHERE e.id=?""", (evidence_id,)
    ).fetchone()


def save_evidence(session_id: int, evidence: InspectionEvidence) -> dict:
    width = evidence.width
    with connect() as con:
        cursor = con.execute(
            """INSERT INTO inspection_evidence(session_id,camera_id,frame_sequence,captured_at,payload_ref,
            position_ft,position_source,calibration_profile_id,calibration_version,measured_span_px,
            target_width_in,measured_width_in,deviation_in,status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (session_id,evidence.camera_id,evidence.frame_sequence,evidence.captured_at.isoformat(),evidence.payload_ref,
             evidence.position_ft,evidence.position_source,evidence.calibration_profile_id,evidence.calibration_version,
             evidence.measured_span_px,width.target_width_in,width.measured_width_in,width.absolute_deviation_in,width.status.value),
        )
        evidence_id = cursor.lastrowid
        if evidence.geometry is not None:
            g = evidence.geometry
            con.execute(
                """INSERT INTO inspection_geometry(evidence_id,estimator_id,left_x,right_x_exclusive,row_y,threshold,
                sampled_rows,span_spread_px,left_edge_spread_px,right_edge_spread_px,min_edge_contrast,
                quality_policy_id,quality_status,quality_reasons_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (evidence_id,g.estimator_id,g.left_x,g.right_x_exclusive,g.row_y,g.threshold,g.sampled_rows,g.span_spread_px,
                 g.left_edge_spread_px,g.right_edge_spread_px,g.min_edge_contrast,g.quality_policy_id,g.quality_status.value,json.dumps(g.quality_reasons)),
            )
        result = dict(_evidence_row(con, evidence_id))
        result["quality_reasons"] = _decode_reasons(result.pop("quality_reasons_json"))
        return result


def list_evidence(session_id: int, limit: int = 250) -> list[dict]:
    if limit < 1 or limit > 1000:
        raise ValueError("limit must be between 1 and 1000")
    with connect() as con:
        rows = con.execute(
            """SELECT e.*, g.estimator_id, g.left_x, g.right_x_exclusive,
            g.row_y AS geometry_row_y, g.threshold AS geometry_threshold, g.sampled_rows,
            g.span_spread_px, g.left_edge_spread_px, g.right_edge_spread_px, g.min_edge_contrast,
            g.quality_policy_id, g.quality_status, g.quality_reasons_json
            FROM inspection_evidence e LEFT JOIN inspection_geometry g ON g.evidence_id=e.id
            WHERE e.session_id=? ORDER BY e.position_ft DESC, e.id DESC LIMIT ?""", (session_id, limit)
        ).fetchall()
        results=[]
        for row in rows:
            result=dict(row)
            result["quality_reasons"]=_decode_reasons(result.pop("quality_reasons_json"))
            results.append(result)
        return results


def evidence_summary(session_id: int) -> dict:
    with connect() as con:
        row=con.execute(
            """SELECT COUNT(*) total,
            SUM(CASE WHEN e.status='PASS' THEN 1 ELSE 0 END) pass_count,
            SUM(CASE WHEN e.status='WARNING' THEN 1 ELSE 0 END) warning_count,
            SUM(CASE WHEN e.status='FAIL' THEN 1 ELSE 0 END) fail_count,
            SUM(CASE WHEN g.quality_status='high-confidence' THEN 1 ELSE 0 END) high_confidence_geometry,
            SUM(CASE WHEN g.quality_status='degraded' THEN 1 ELSE 0 END) degraded_geometry,
            MIN(e.measured_width_in) min_width_in, MAX(e.measured_width_in) max_width_in
            FROM inspection_evidence e LEFT JOIN inspection_geometry g ON g.evidence_id=e.id WHERE e.session_id=?""", (session_id,)
        ).fetchone()
        return {"total":row["total"] or 0,"pass":row["pass_count"] or 0,"warning":row["warning_count"] or 0,
                "fail":row["fail_count"] or 0,"high_confidence_geometry":row["high_confidence_geometry"] or 0,
                "degraded_geometry":row["degraded_geometry"] or 0,"min_width_in":row["min_width_in"],"max_width_in":row["max_width_in"]}
