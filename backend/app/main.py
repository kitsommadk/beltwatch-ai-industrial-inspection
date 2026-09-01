from contextlib import asynccontextmanager
from datetime import datetime, timezone
from functools import lru_cache
import os
from random import uniform

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

from .database import connect, initialize
from .detection import SimulatedDetector
from .evidence_store import evidence_summary, initialize_evidence_store, list_evidence, save_evidence
from .runtime import InspectionRuntime, RuntimeConfigurationError, build_runtime
from .schemas import DetectionRequest, EvidenceCaptureRequest, EventReview, ProgressInput, SessionInput


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def row_dict(row):
    return dict(row) if row else None


def current_session(con):
    return con.execute("SELECT * FROM sessions ORDER BY id DESC LIMIT 1").fetchone()


def audit(con, action: str, detail: str) -> None:
    con.execute(
        "INSERT INTO audit_log(created_at, action, detail) VALUES (?, ?, ?)",
        (now(), action, detail),
    )


@lru_cache
def get_runtime() -> InspectionRuntime:
    """Resolve the configured inspection providers once per process.

    Tests can override this FastAPI dependency without touching production code.
    """
    try:
        return build_runtime()
    except RuntimeConfigurationError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc


@asynccontextmanager
async def lifespan(_app: FastAPI):
    initialize()
    initialize_evidence_store()
    yield


app = FastAPI(
    title="BeltWatch AI Pilot API",
    description="Local-first inspection workflow API. Detection is simulated in this public portfolio build.",
    version="0.5.0",
    lifespan=lifespan,
)

origins = [x.strip() for x in os.getenv("BELTWATCH_ALLOWED_ORIGINS", "http://localhost:5173").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

detector = SimulatedDetector()


@app.get("/api/health")
def health(runtime: InspectionRuntime = Depends(get_runtime)):
    return {
        "status": "online",
        "mode": runtime.mode,
        "database": "sqlite",
        "machine_control": False,
    }


@app.get("/api/system")
def system_status(runtime: InspectionRuntime = Depends(get_runtime)):
    return {
        "mode": runtime.mode,
        "components": [
            {"name": "Top camera", "status": "simulated" if runtime.mode == "simulation" else "configured"},
            {"name": "Bottom camera", "status": "simulated" if runtime.mode == "simulation" else "configured"},
            {"name": "Controlled lighting", "status": "ready"},
            {"name": "Edge computer", "status": "healthy"},
            {"name": "Local database", "status": "recording"},
            {"name": "Storage", "status": "82% free"},
        ],
    }


@app.get("/api/session")
def get_session():
    with connect() as con:
        session = current_session(con)
        if session is None:
            return None
        result = row_dict(session)
        result["completion_pct"] = round(min(100, 100 * result["footage_ft"] / result["target_length_ft"]), 1)
        return result


@app.post("/api/session/start")
def start_session(payload: SessionInput):
    timestamp = now()
    with connect() as con:
        con.execute(
            """INSERT INTO sessions(
                roll_number, work_order, operator, target_width_in, tolerance_in,
                target_length_ft, footage_ft, current_width_in, status, started_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, 'inspecting', ?, ?)""",
            (
                payload.roll_number,
                payload.work_order,
                payload.operator,
                payload.target_width_in,
                payload.tolerance_in,
                payload.target_length_ft,
                payload.target_width_in,
                timestamp,
                timestamp,
            ),
        )
        session = current_session(con)
        audit(con, "session.started", f"session={session['id']} roll={payload.roll_number}")
        return row_dict(session)


@app.post("/api/session/pause")
def pause_session():
    with connect() as con:
        session = current_session(con)
        if session is None:
            raise HTTPException(404, "No inspection session exists")
        status = "paused" if session["status"] == "inspecting" else "inspecting"
        con.execute("UPDATE sessions SET status=?, updated_at=? WHERE id=?", (status, now(), session["id"]))
        audit(con, f"session.{status}", f"session={session['id']}")
        return row_dict(current_session(con))


@app.post("/api/session/progress")
def progress_session(payload: ProgressInput):
    with connect() as con:
        session = current_session(con)
        if session is None:
            raise HTTPException(404, "No inspection session exists")
        if session["status"] != "inspecting":
            return row_dict(session)
        footage = min(session["target_length_ft"], session["footage_ft"] + payload.delta_ft)
        status = "complete" if footage >= session["target_length_ft"] else "inspecting"
        width = round(session["target_width_in"] + uniform(-0.035, 0.035), 3)
        con.execute(
            "UPDATE sessions SET footage_ft=?, current_width_in=?, status=?, updated_at=? WHERE id=?",
            (footage, width, status, now(), session["id"]),
        )
        if status == "complete":
            audit(con, "session.complete", f"session={session['id']} footage={footage}")
        return row_dict(current_session(con))


@app.post("/api/evidence/capture")
def capture_evidence(
    payload: EvidenceCaptureRequest,
    runtime: InspectionRuntime = Depends(get_runtime),
):
    """Capture and persist traceable dimensional evidence for the active session.

    In the public simulation build, measured_span_px is supplied by the caller.
    A later vision adapter will calculate this value from detected belt edges.
    """
    with connect() as con:
        session = current_session(con)
        if session is None:
            raise HTTPException(409, "Start an inspection session before capturing evidence")
        if session["status"] != "inspecting":
            raise HTTPException(409, "Inspection evidence can only be captured while the session is inspecting")
        session_id = session["id"]
        target_width = session["target_width_in"]
        warning_tolerance = session["tolerance_in"]

    try:
        service = runtime.service_for(payload.camera)
        evidence = service.capture_width(
            measured_span_px=payload.measured_span_px,
            target_width_in=target_width,
            warning_tolerance_in=warning_tolerance,
            fail_tolerance_in=warning_tolerance * 2,
        )
    except (RuntimeConfigurationError, ValueError) as exc:
        raise HTTPException(422, str(exc)) from exc

    saved = save_evidence(session_id, evidence)
    with connect() as con:
        con.execute(
            "UPDATE sessions SET current_width_in=?, updated_at=? WHERE id=?",
            (saved["measured_width_in"], now(), session_id),
        )
        audit(
            con,
            "evidence.captured",
            f"evidence={saved['id']} camera={saved['camera_id']} position_ft={saved['position_ft']} status={saved['status']}",
        )
    return saved


@app.get("/api/evidence")
def get_evidence(limit: int = Query(default=250, ge=1, le=1000)):
    with connect() as con:
        session = current_session(con)
        if session is None:
            return []
        session_id = session["id"]
    return list_evidence(session_id, limit=limit)


@app.get("/api/evidence/summary")
def get_evidence_summary():
    with connect() as con:
        session = current_session(con)
        if session is None:
            return {
                "total": 0,
                "pass": 0,
                "warning": 0,
                "fail": 0,
                "min_width_in": None,
                "max_width_in": None,
            }
        session_id = session["id"]
    return evidence_summary(session_id)


@app.get("/api/events")
def list_events():
    with connect() as con:
        session = current_session(con)
        if session is None:
            return []
        return [
            dict(row)
            for row in con.execute(
                "SELECT * FROM events WHERE session_id=? ORDER BY id DESC LIMIT 100", (session["id"],)
            )
        ]


@app.post("/api/events/simulate")
def simulate_event(payload: DetectionRequest):
    with connect() as con:
        session = current_session(con)
        if session is None:
            raise HTTPException(409, "Start an inspection session before creating events")
        detection = detector.detect(payload.kind, session["target_width_in"], payload.camera)
        location = min(session["target_length_ft"], session["footage_ft"] + round(uniform(1, 18), 1))
        cursor = con.execute(
            """INSERT INTO events(
                session_id, created_at, damage_type, severity, camera, location_ft,
                measured_width_in, confidence, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'open')""",
            (
                session["id"],
                now(),
                detection.damage_type,
                detection.severity,
                detection.camera,
                location,
                detection.measured_width_in,
                detection.confidence,
            ),
        )
        event = con.execute("SELECT * FROM events WHERE id=?", (cursor.lastrowid,)).fetchone()
        audit(con, "event.created", f"event={event['id']} type={event['damage_type']}")
        return row_dict(event)


@app.post("/api/events/{event_id}/review")
def review_event(event_id: int, payload: EventReview):
    with connect() as con:
        event = con.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone()
        if event is None:
            raise HTTPException(404, "Event not found")
        con.execute(
            "UPDATE events SET status=?, review_note=?, reviewed_at=? WHERE id=?",
            (payload.status, payload.note, now(), event_id),
        )
        audit(con, "event.reviewed", f"event={event_id} status={payload.status}")
        return row_dict(con.execute("SELECT * FROM events WHERE id=?", (event_id,)).fetchone())


@app.get("/api/summary")
def summary():
    with connect() as con:
        session = current_session(con)
        if session is None:
            return {"open_events": 0, "total_events": 0, "false_positives": 0}
        counts = con.execute(
            """SELECT COUNT(*) total,
                SUM(CASE WHEN status='open' THEN 1 ELSE 0 END) open_count,
                SUM(CASE WHEN status='false_positive' THEN 1 ELSE 0 END) false_count
            FROM events WHERE session_id=?""",
            (session["id"],),
        ).fetchone()
        return {
            "open_events": counts["open_count"] or 0,
            "total_events": counts["total"] or 0,
            "false_positives": counts["false_count"] or 0,
        }


@app.get("/api/audit")
def audit_log():
    with connect() as con:
        return [dict(row) for row in con.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 100")]
