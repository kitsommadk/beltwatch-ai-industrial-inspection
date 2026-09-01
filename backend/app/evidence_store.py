"""SQLite persistence for traceable BeltWatch inspection evidence."""

import json

from .database import connect
from .evidence import InspectionEvidence


EVIDENCE_SCHEMA_VERSION = 8


def _geometry_columns(con) -> set[str]:
    return {row["name"] for row in con.execute("PRAGMA table_info(inspection_geometry)").fetchall()}


def _migrate_v2_to_v3(con) -> None:
    columns = _geometry_columns(con)
    if "quality_policy_id" not in columns: con.execute("ALTER TABLE inspection_geometry ADD COLUMN quality_policy_id TEXT")
    if "quality_status" not in columns: con.execute("ALTER TABLE inspection_geometry ADD COLUMN quality_status TEXT")
    if "quality_reasons_json" not in columns: con.execute("ALTER TABLE inspection_geometry ADD COLUMN quality_reasons_json TEXT")
    con.execute("UPDATE evidence_schema_metadata SET schema_version=3 WHERE singleton_id=1")


def _migrate_v3_to_v4(con) -> None:
    columns = _geometry_columns(con)
    if "left_edge_spread_px" not in columns: con.execute("ALTER TABLE inspection_geometry ADD COLUMN left_edge_spread_px INTEGER")
    if "right_edge_spread_px" not in columns: con.execute("ALTER TABLE inspection_geometry ADD COLUMN right_edge_spread_px INTEGER")
    con.execute("UPDATE evidence_schema_metadata SET schema_version=4 WHERE singleton_id=1")


def _migrate_v4_to_v5(con) -> None:
    if "min_edge_contrast" not in _geometry_columns(con): con.execute("ALTER TABLE inspection_geometry ADD COLUMN min_edge_contrast REAL")
    con.execute("UPDATE evidence_schema_metadata SET schema_version=5 WHERE singleton_id=1")


def _migrate_v5_to_v6(con) -> None:
    if "min_edge_sharpness" not in _geometry_columns(con): con.execute("ALTER TABLE inspection_geometry ADD COLUMN min_edge_sharpness REAL")
    con.execute("UPDATE evidence_schema_metadata SET schema_version=6 WHERE singleton_id=1")


def _migrate_v6_to_v7(con) -> None:
    con.execute("UPDATE evidence_schema_metadata SET schema_version=7 WHERE singleton_id=1")


def _migrate_v7_to_v8(con) -> None:
    """Rebuild evidence identity so one physical frame may contain multiple belt lanes."""
    con.execute("PRAGMA foreign_keys = OFF")
    try:
        con.execute("ALTER TABLE inspection_evidence RENAME TO inspection_evidence_v7")
        con.execute("""CREATE TABLE inspection_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NOT NULL, camera_id TEXT NOT NULL,
            frame_sequence INTEGER NOT NULL, lane_id TEXT NOT NULL DEFAULT 'belt', captured_at TEXT NOT NULL,
            payload_ref TEXT NOT NULL, position_ft REAL NOT NULL, position_source TEXT NOT NULL,
            calibration_profile_id TEXT NOT NULL, calibration_version INTEGER NOT NULL, measured_span_px REAL NOT NULL,
            target_width_in REAL NOT NULL, measured_width_in REAL NOT NULL, deviation_in REAL NOT NULL, status TEXT NOT NULL,
            FOREIGN KEY(session_id) REFERENCES sessions(id), UNIQUE(session_id, camera_id, frame_sequence, lane_id))""")
        con.execute("""INSERT INTO inspection_evidence(id,session_id,camera_id,frame_sequence,lane_id,captured_at,payload_ref,
            position_ft,position_source,calibration_profile_id,calibration_version,measured_span_px,target_width_in,
            measured_width_in,deviation_in,status)
            SELECT id,session_id,camera_id,frame_sequence,'belt',captured_at,payload_ref,position_ft,position_source,
            calibration_profile_id,calibration_version,measured_span_px,target_width_in,measured_width_in,deviation_in,status
            FROM inspection_evidence_v7""")
        con.execute("DROP TABLE inspection_evidence_v7")
        con.execute("CREATE INDEX IF NOT EXISTS idx_evidence_session_position ON inspection_evidence(session_id, position_ft)")
        con.execute("UPDATE evidence_schema_metadata SET schema_version=8 WHERE singleton_id=1")
    finally:
        con.execute("PRAGMA foreign_keys = ON")


def initialize_evidence_store() -> None:
    with connect() as con:
        con.executescript("""
        CREATE TABLE IF NOT EXISTS inspection_evidence (
            id INTEGER PRIMARY KEY AUTOINCREMENT, session_id INTEGER NOT NULL, camera_id TEXT NOT NULL,
            frame_sequence INTEGER NOT NULL, lane_id TEXT NOT NULL DEFAULT 'belt', captured_at TEXT NOT NULL,
            payload_ref TEXT NOT NULL, position_ft REAL NOT NULL, position_source TEXT NOT NULL,
            calibration_profile_id TEXT NOT NULL, calibration_version INTEGER NOT NULL, measured_span_px REAL NOT NULL,
            target_width_in REAL NOT NULL, measured_width_in REAL NOT NULL, deviation_in REAL NOT NULL, status TEXT NOT NULL,
            FOREIGN KEY(session_id) REFERENCES sessions(id), UNIQUE(session_id, camera_id, frame_sequence, lane_id));
        CREATE TABLE IF NOT EXISTS evidence_schema_metadata (singleton_id INTEGER PRIMARY KEY CHECK(singleton_id=1), schema_version INTEGER NOT NULL CHECK(schema_version>0));
        CREATE TABLE IF NOT EXISTS inspection_geometry (
            evidence_id INTEGER PRIMARY KEY, estimator_id TEXT NOT NULL, left_x INTEGER NOT NULL, right_x_exclusive INTEGER NOT NULL,
            row_y INTEGER NOT NULL, threshold REAL NOT NULL, sampled_rows INTEGER NOT NULL, span_spread_px INTEGER NOT NULL,
            left_edge_spread_px INTEGER, right_edge_spread_px INTEGER, min_edge_contrast REAL, min_edge_sharpness REAL,
            quality_policy_id TEXT, quality_status TEXT, quality_reasons_json TEXT,
            FOREIGN KEY(evidence_id) REFERENCES inspection_evidence(id) ON DELETE CASCADE,
            CHECK(right_x_exclusive>left_x), CHECK(sampled_rows>0), CHECK(span_spread_px>=0));
        CREATE TABLE IF NOT EXISTS inspection_frame_quality (
            evidence_id INTEGER PRIMARY KEY, policy_id TEXT NOT NULL, status TEXT NOT NULL, sampled_pixels INTEGER NOT NULL,
            mean_intensity REAL NOT NULL, p05_intensity REAL NOT NULL, p95_intensity REAL NOT NULL, dynamic_range REAL NOT NULL,
            low_clipped_fraction REAL NOT NULL, high_clipped_fraction REAL NOT NULL, reasons_json TEXT NOT NULL,
            FOREIGN KEY(evidence_id) REFERENCES inspection_evidence(id) ON DELETE CASCADE,
            CHECK(sampled_pixels>0), CHECK(dynamic_range>=0), CHECK(low_clipped_fraction>=0 AND low_clipped_fraction<=1), CHECK(high_clipped_fraction>=0 AND high_clipped_fraction<=1));
        CREATE INDEX IF NOT EXISTS idx_evidence_session_position ON inspection_evidence(session_id, position_ft);
        """)
        con.execute("INSERT OR IGNORE INTO evidence_schema_metadata(singleton_id,schema_version) VALUES (1,?)", (EVIDENCE_SCHEMA_VERSION,))
        stored=con.execute("SELECT schema_version FROM evidence_schema_metadata WHERE singleton_id=1").fetchone()[0]
        if stored==2: _migrate_v2_to_v3(con); stored=3
        if stored==3: _migrate_v3_to_v4(con); stored=4
        if stored==4: _migrate_v4_to_v5(con); stored=5
        if stored==5: _migrate_v5_to_v6(con); stored=6
        if stored==6: _migrate_v6_to_v7(con); stored=7
        if stored==7: _migrate_v7_to_v8(con); stored=8
        if stored != EVIDENCE_SCHEMA_VERSION:
            raise RuntimeError(f"evidence schema version {stored} does not match application version {EVIDENCE_SCHEMA_VERSION}; explicit evidence migration is required")


def _decode_reasons(value): return None if value is None else list(json.loads(value))


def _evidence_select() -> str:
    return """SELECT e.*, g.estimator_id,g.left_x,g.right_x_exclusive,g.row_y AS geometry_row_y,g.threshold AS geometry_threshold,g.sampled_rows,
    g.span_spread_px,g.left_edge_spread_px,g.right_edge_spread_px,g.min_edge_contrast,g.min_edge_sharpness,g.quality_policy_id,g.quality_status,g.quality_reasons_json,
    fq.policy_id AS frame_quality_policy_id,fq.status AS frame_quality_status,fq.sampled_pixels AS frame_sampled_pixels,
    fq.mean_intensity AS frame_mean_intensity,fq.p05_intensity AS frame_p05_intensity,fq.p95_intensity AS frame_p95_intensity,
    fq.dynamic_range AS frame_dynamic_range,fq.low_clipped_fraction AS frame_low_clipped_fraction,fq.high_clipped_fraction AS frame_high_clipped_fraction,
    fq.reasons_json AS frame_quality_reasons_json FROM inspection_evidence e LEFT JOIN inspection_geometry g ON g.evidence_id=e.id
    LEFT JOIN inspection_frame_quality fq ON fq.evidence_id=e.id"""


def _decode_row(row):
    result=dict(row); result["quality_reasons"]=_decode_reasons(result.pop("quality_reasons_json")); result["frame_quality_reasons"]=_decode_reasons(result.pop("frame_quality_reasons_json")); return result


def _evidence_row(con,evidence_id): return con.execute(_evidence_select()+" WHERE e.id=?",(evidence_id,)).fetchone()


def save_evidence(session_id: int, evidence: InspectionEvidence, *, lane_id: str = "belt") -> dict:
    if not lane_id.strip(): raise ValueError("lane_id must not be empty")
    width=evidence.width
    with connect() as con:
        cursor=con.execute("""INSERT INTO inspection_evidence(session_id,camera_id,frame_sequence,lane_id,captured_at,payload_ref,position_ft,position_source,
        calibration_profile_id,calibration_version,measured_span_px,target_width_in,measured_width_in,deviation_in,status) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (session_id,evidence.camera_id,evidence.frame_sequence,lane_id,evidence.captured_at.isoformat(),evidence.payload_ref,evidence.position_ft,evidence.position_source,
        evidence.calibration_profile_id,evidence.calibration_version,evidence.measured_span_px,width.target_width_in,width.measured_width_in,width.absolute_deviation_in,width.status.value))
        evidence_id=cursor.lastrowid
        if evidence.geometry is not None:
            g=evidence.geometry; con.execute("""INSERT INTO inspection_geometry(evidence_id,estimator_id,left_x,right_x_exclusive,row_y,threshold,sampled_rows,span_spread_px,left_edge_spread_px,right_edge_spread_px,min_edge_contrast,min_edge_sharpness,quality_policy_id,quality_status,quality_reasons_json) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (evidence_id,g.estimator_id,g.left_x,g.right_x_exclusive,g.row_y,g.threshold,g.sampled_rows,g.span_spread_px,g.left_edge_spread_px,g.right_edge_spread_px,g.min_edge_contrast,g.min_edge_sharpness,g.quality_policy_id,g.quality_status.value,json.dumps(g.quality_reasons)))
        if evidence.frame_quality is not None:
            fq=evidence.frame_quality; con.execute("""INSERT INTO inspection_frame_quality(evidence_id,policy_id,status,sampled_pixels,mean_intensity,p05_intensity,p95_intensity,dynamic_range,low_clipped_fraction,high_clipped_fraction,reasons_json) VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
            (evidence_id,fq.policy_id,fq.status.value,fq.sampled_pixels,fq.mean_intensity,fq.p05_intensity,fq.p95_intensity,fq.dynamic_range,fq.low_clipped_fraction,fq.high_clipped_fraction,json.dumps(fq.reasons)))
        return _decode_row(_evidence_row(con,evidence_id))


def list_evidence(session_id:int,limit:int=250):
    if limit<1 or limit>1000: raise ValueError("limit must be between 1 and 1000")
    with connect() as con:
        return [_decode_row(r) for r in con.execute(_evidence_select()+" WHERE e.session_id=? ORDER BY e.position_ft DESC,e.id DESC LIMIT ?",(session_id,limit)).fetchall()]


def evidence_summary(session_id:int):
    with connect() as con:
        row=con.execute("""SELECT COUNT(*) total,SUM(CASE WHEN e.status='PASS' THEN 1 ELSE 0 END) pass_count,SUM(CASE WHEN e.status='WARNING' THEN 1 ELSE 0 END) warning_count,
        SUM(CASE WHEN e.status='FAIL' THEN 1 ELSE 0 END) fail_count,SUM(CASE WHEN g.quality_status='high-confidence' THEN 1 ELSE 0 END) high_confidence_geometry,
        SUM(CASE WHEN g.quality_status='degraded' THEN 1 ELSE 0 END) degraded_geometry,SUM(CASE WHEN fq.status='high-confidence' THEN 1 ELSE 0 END) high_confidence_frame_quality,
        SUM(CASE WHEN fq.status='degraded' THEN 1 ELSE 0 END) degraded_frame_quality,MIN(e.measured_width_in) min_width_in,MAX(e.measured_width_in) max_width_in
        FROM inspection_evidence e LEFT JOIN inspection_geometry g ON g.evidence_id=e.id LEFT JOIN inspection_frame_quality fq ON fq.evidence_id=e.id WHERE e.session_id=?""",(session_id,)).fetchone()
        return {"total":row["total"] or 0,"pass":row["pass_count"] or 0,"warning":row["warning_count"] or 0,"fail":row["fail_count"] or 0,
        "high_confidence_geometry":row["high_confidence_geometry"] or 0,"degraded_geometry":row["degraded_geometry"] or 0,"high_confidence_frame_quality":row["high_confidence_frame_quality"] or 0,
        "degraded_frame_quality":row["degraded_frame_quality"] or 0,"min_width_in":row["min_width_in"],"max_width_in":row["max_width_in"]}
