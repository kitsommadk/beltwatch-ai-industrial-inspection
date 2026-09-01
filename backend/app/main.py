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
from .multilane_evidence import capture_two_lane_width_auto
from .runtime import InspectionRuntime, RuntimeConfigurationError, build_runtime
from .schemas import DetectionRequest, EvidenceAutoCaptureRequest, EvidenceCaptureRequest, EventReview, ProgressInput, SessionInput


def now() -> str: return datetime.now(timezone.utc).isoformat()
def row_dict(row): return dict(row) if row else None
def current_session(con): return con.execute("SELECT * FROM sessions ORDER BY id DESC LIMIT 1").fetchone()
def _lane_targets(con, session_id: int) -> dict[str, float]: return {r["lane_id"]: r["target_width_in"] for r in con.execute("SELECT lane_id,target_width_in FROM session_lanes WHERE session_id=? ORDER BY lane_id",(session_id,))}
def _session_response(con, session):
    if session is None: return None
    result=row_dict(session); result["lane_targets"]=_lane_targets(con,session["id"]); return result
def audit(con,action:str,detail:str)->None: con.execute("INSERT INTO audit_log(created_at,action,detail) VALUES (?,?,?)",(now(),action,detail))

@lru_cache
def get_runtime()->InspectionRuntime:
    try: return build_runtime()
    except RuntimeConfigurationError as exc: raise HTTPException(status_code=503,detail=str(exc)) from exc

@asynccontextmanager
async def lifespan(_app:FastAPI): initialize(); initialize_evidence_store(); yield

app=FastAPI(title="BeltWatch AI Pilot API",description="Local-first inspection workflow API with explicit simulation and replay validation modes.",version="0.8.0",lifespan=lifespan)
origins=[x.strip() for x in os.getenv("BELTWATCH_ALLOWED_ORIGINS","http://localhost:5173").split(",")]
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=False,allow_methods=["GET","POST"],allow_headers=["Content-Type"])
detector=SimulatedDetector()

@app.get("/api/health")
def health(runtime:InspectionRuntime=Depends(get_runtime)): return {"status":"online","mode":runtime.mode,"database":"sqlite","machine_control":False}

def _camera_component(runtime,camera_id,label):
    service=runtime.service_for(camera_id); camera=service.camera; health_fn=getattr(camera,"health",None); h=health_fn() if callable(health_fn) else None
    status="simulated" if runtime.mode=="simulation" else "replay" if runtime.mode=="replay" else "configured"; component={"name":label,"status":status}
    if h is not None: component["health"]={"connected":h.connected,"stale":h.stale,"frames_captured":h.frames_captured,"capture_failures":h.capture_failures,"last_frame_at":h.last_frame_at.isoformat() if h.last_frame_at else None}
    return component

@app.get("/api/system")
def system_status(runtime:InspectionRuntime=Depends(get_runtime)): return {"mode":runtime.mode,"components":[_camera_component(runtime,"top","Top camera"),_camera_component(runtime,"bottom","Bottom camera"),{"name":"Controlled lighting","status":"ready"},{"name":"Edge computer","status":"healthy"},{"name":"Local database","status":"recording"},{"name":"Storage","status":"not-measured"}]}

@app.get("/api/session")
def get_session():
    with connect() as con:
        s=current_session(con)
        if s is None:return None
        result=_session_response(con,s); result["completion_pct"]=round(min(100,100*result["footage_ft"]/result["target_length_ft"]),1); return result

@app.post("/api/session/start")
def start_session(payload:SessionInput):
    timestamp=now()
    with connect() as con:
        cursor=con.execute("INSERT INTO sessions(roll_number,work_order,operator,target_width_in,tolerance_in,target_length_ft,footage_ft,current_width_in,status,started_at,updated_at,run_layout) VALUES (?,?,?,?,?,?,0,?,'inspecting',?,?,?)",(payload.roll_number,payload.work_order,payload.operator,payload.target_width_in,payload.tolerance_in,payload.target_length_ft,payload.target_width_in,timestamp,timestamp,payload.run_layout))
        sid=cursor.lastrowid; targets={"belt":payload.target_width_in} if payload.run_layout=="single" else dict(payload.lane_targets or {})
        con.executemany("INSERT INTO session_lanes(session_id,lane_id,target_width_in) VALUES (?,?,?)",[(sid,l,w) for l,w in targets.items()]); s=con.execute("SELECT * FROM sessions WHERE id=?",(sid,)).fetchone(); audit(con,"session.started",f"session={sid} roll={payload.roll_number} layout={payload.run_layout} lanes={','.join(sorted(targets))}"); return _session_response(con,s)

@app.post("/api/session/pause")
def pause_session():
    with connect() as con:
        s=current_session(con)
        if s is None:raise HTTPException(404,"No inspection session exists")
        status="paused" if s["status"]=="inspecting" else "inspecting"; con.execute("UPDATE sessions SET status=?,updated_at=? WHERE id=?",(status,now(),s["id"])); audit(con,f"session.{status}",f"session={s['id']}"); return _session_response(con,current_session(con))

@app.post("/api/session/progress")
def progress_session(payload:ProgressInput):
    with connect() as con:
        s=current_session(con)
        if s is None:raise HTTPException(404,"No inspection session exists")
        if s["status"]!="inspecting":return _session_response(con,s)
        footage=min(s["target_length_ft"],s["footage_ft"]+payload.delta_ft); status="complete" if footage>=s["target_length_ft"] else "inspecting"
        if s["run_layout"]=="single":
            width=round(s["target_width_in"]+uniform(-.035,.035),3)
            con.execute("UPDATE sessions SET footage_ft=?,current_width_in=?,status=?,updated_at=? WHERE id=?",(footage,width,status,now(),s["id"]))
        else:
            con.execute("UPDATE sessions SET footage_ft=?,status=?,updated_at=? WHERE id=?",(footage,status,now(),s["id"]))
        if status=="complete":audit(con,"session.complete",f"session={s['id']} footage={footage}")
        return _session_response(con,current_session(con))

def _active_session_context():
    with connect() as con:
        s=current_session(con)
        if s is None:raise HTTPException(409,"Start an inspection session before capturing evidence")
        if s["status"]!="inspecting":raise HTTPException(409,"Inspection evidence can only be captured while the session is inspecting")
        return {"session_id":s["id"],"run_layout":s["run_layout"],"target_width_in":s["target_width_in"],"tolerance_in":s["tolerance_in"],"lane_targets":_lane_targets(con,s["id"])}

def _persist_captured_evidence(session_id,evidence,*,lane_id="belt",update_current_width=True):
    saved=save_evidence(session_id,evidence,lane_id=lane_id)
    with connect() as con:
        if update_current_width: con.execute("UPDATE sessions SET current_width_in=?,updated_at=? WHERE id=?",(saved["measured_width_in"],now(),session_id))
        audit(con,"evidence.captured",f"evidence={saved['id']} lane={lane_id} camera={saved['camera_id']} position_ft={saved['position_ft']} status={saved['status']}")
    return saved

@app.post("/api/evidence/capture")
def capture_evidence(payload:EvidenceCaptureRequest,runtime:InspectionRuntime=Depends(get_runtime)):
    ctx=_active_session_context()
    if ctx["run_layout"]!="single":raise HTTPException(409,"manual pixel-span capture is only available for single-belt sessions")
    try:
        service=runtime.service_for(payload.camera); evidence=service.capture_width(measured_span_px=payload.measured_span_px,target_width_in=ctx["target_width_in"],warning_tolerance_in=ctx["tolerance_in"],fail_tolerance_in=ctx["tolerance_in"]*2)
    except (RuntimeConfigurationError,ValueError,RuntimeError,EOFError) as exc:raise HTTPException(422,str(exc)) from exc
    return _persist_captured_evidence(ctx["session_id"],evidence)

@app.post("/api/evidence/capture-auto")
def capture_evidence_auto(payload:EvidenceAutoCaptureRequest,runtime:InspectionRuntime=Depends(get_runtime)):
    ctx=_active_session_context()
    try:
        if ctx["run_layout"]=="single":
            service=runtime.service_for(payload.camera); estimator=runtime.estimator_for(payload.camera); evidence=service.capture_width_auto(estimator=estimator,target_width_in=ctx["target_width_in"],warning_tolerance_in=ctx["tolerance_in"],fail_tolerance_in=ctx["tolerance_in"]*2)
            return _persist_captured_evidence(ctx["session_id"],evidence,lane_id="belt")
        if set(ctx["lane_targets"])!={"belt-a","belt-b"}:raise RuntimeConfigurationError("slit-two-lane session is missing exact belt-a/b targets")
        service=runtime.two_lane_service_for(payload.camera); estimator=runtime.two_lane_estimator_for(payload.camera)
        lanes=capture_two_lane_width_auto(service,estimator,ctx["lane_targets"],ctx["tolerance_in"],ctx["tolerance_in"]*2)
        saved=[_persist_captured_evidence(ctx["session_id"],lane.evidence,lane_id=lane.lane_id,update_current_width=False) for lane in lanes]
        with connect() as con: audit(con,"evidence.multilane_captured",f"session={ctx['session_id']} camera={payload.camera} frame={saved[0]['frame_sequence']} lanes=belt-a,belt-b")
        return {"run_layout":"slit-two-lane","shared_frame_sequence":saved[0]["frame_sequence"],"shared_position_ft":saved[0]["position_ft"],"records":saved}
    except (RuntimeConfigurationError,ValueError,RuntimeError,EOFError) as exc:raise HTTPException(422,str(exc)) from exc

@app.get("/api/evidence")
def get_evidence(limit:int=Query(default=250,ge=1,le=1000)):
    with connect() as con:
        s=current_session(con)
        if s is None:return []
        sid=s["id"]
    return list_evidence(sid,limit=limit)

@app.get("/api/evidence/summary")
def get_evidence_summary():
    with connect() as con:
        s=current_session(con)
        if s is None:return {"total":0,"pass":0,"warning":0,"fail":0,"min_width_in":None,"max_width_in":None}
        sid=s["id"]
    return evidence_summary(sid)

@app.get("/api/events")
def list_events():
    with connect() as con:
        s=current_session(con)
        if s is None:return []
        return [dict(r) for r in con.execute("SELECT * FROM events WHERE session_id=? ORDER BY id DESC LIMIT 100",(s["id"],))]

@app.post("/api/events/simulate")
def simulate_event(payload:DetectionRequest):
    with connect() as con:
        s=current_session(con)
        if s is None:raise HTTPException(409,"Start an inspection session before creating events")
        if s["run_layout"]!="single":raise HTTPException(409,"simulated width events are only available for single-belt sessions until lane-aware event simulation is implemented")
        d=detector.detect(payload.kind,s["target_width_in"],payload.camera); location=min(s["target_length_ft"],s["footage_ft"]+round(uniform(1,18),1)); cursor=con.execute("INSERT INTO events(session_id,created_at,damage_type,severity,camera,location_ft,measured_width_in,confidence,status) VALUES (?,?,?,?,?,?,?,?,'open')",(s["id"],now(),d.damage_type,d.severity,d.camera,location,d.measured_width_in,d.confidence)); event=con.execute("SELECT * FROM events WHERE id=?",(cursor.lastrowid,)).fetchone(); audit(con,"event.created",f"event={event['id']} type={event['damage_type']}"); return row_dict(event)

@app.post("/api/events/{event_id}/review")
def review_event(event_id:int,payload:EventReview):
    with connect() as con:
        event=con.execute("SELECT * FROM events WHERE id=?",(event_id,)).fetchone()
        if event is None:raise HTTPException(404,"Event not found")
        con.execute("UPDATE events SET status=?,review_note=?,reviewed_at=? WHERE id=?",(payload.status,payload.note,now(),event_id)); audit(con,"event.reviewed",f"event={event_id} status={payload.status}"); return row_dict(con.execute("SELECT * FROM events WHERE id=?",(event_id,)).fetchone())

@app.get("/api/summary")
def summary():
    with connect() as con:
        s=current_session(con)
        if s is None:return {"open_events":0,"total_events":0,"false_positives":0}
        c=con.execute("SELECT COUNT(*) total,SUM(CASE WHEN status='open' THEN 1 ELSE 0 END) open_count,SUM(CASE WHEN status='false_positive' THEN 1 ELSE 0 END) false_count FROM events WHERE session_id=?",(s["id"],)).fetchone(); return {"open_events":c["open_count"] or 0,"total_events":c["total"] or 0,"false_positives":c["false_count"] or 0}

@app.get("/api/audit")
def audit_log():
    with connect() as con:return [dict(r) for r in con.execute("SELECT * FROM audit_log ORDER BY id DESC LIMIT 100")]
