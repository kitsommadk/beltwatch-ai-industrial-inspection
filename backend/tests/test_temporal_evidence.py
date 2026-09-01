from datetime import datetime
from pathlib import Path

import pytest

from app.database import connect, initialize
from app.evidence import InspectionEvidence
from app.evidence_store import initialize_evidence_store
from app.measurement import WidthMeasurement, WidthStatus
from app.temporal_evidence import assess_evidence_temporally
from app.temporal_quality import TemporalQualityPolicy, TemporalQualityStatus


def _policy():
    return TemporalQualityPolicy(policy_id="temporal-evidence-v1", high_confidence_max_change_per_ft=0.05, valid_max_change_per_ft=0.20)


def _session():
    with connect() as con:
        return con.execute("""INSERT INTO sessions(roll_number,work_order,operator,target_width_in,tolerance_in,target_length_ft,footage_ft,current_width_in,status,updated_at)
        VALUES ('R1','WO1','tester',48,0.1,100,0,48,'inspecting','now')""").lastrowid


def _trusted(session_id, position, width, lane="belt"):
    with connect() as con:
        evidence_id = con.execute("""INSERT INTO inspection_evidence(session_id,camera_id,frame_sequence,lane_id,captured_at,payload_ref,position_ft,position_source,calibration_profile_id,calibration_version,measured_span_px,target_width_in,measured_width_in,deviation_in,status)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (session_id,"top",int(position),lane,"2026-09-01T12:00:00","replay://old",position,"simulated","cal",1,480,48,width,abs(width-48),"PASS")).lastrowid
        con.execute("INSERT INTO inspection_geometry(evidence_id,estimator_id,left_x,right_x_exclusive,row_y,threshold,sampled_rows,span_spread_px,quality_policy_id,quality_status,quality_reasons_json) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (evidence_id,"test",10,490,100,100,5,0,"g","high-confidence","[]"))
        con.execute("INSERT INTO inspection_frame_quality(evidence_id,policy_id,status,sampled_pixels,mean_intensity,p05_intensity,p95_intensity,dynamic_range,low_clipped_fraction,high_clipped_fraction,reasons_json) VALUES (?,?,?,?,?,?,?,?,?,?,?)", (evidence_id,"f","high-confidence",1000,120,40,220,180,0,0,"[]"))


def _evidence(position, width):
    measurement = WidthMeasurement(
        camera_id="top",
        frame_sequence=99,
        calibration_profile_id="cal",
        calibration_version=1,
        position_ft=position,
        measured_width_in=width,
        target_width_in=48.0,
        absolute_deviation_in=abs(width - 48.0),
        status=WidthStatus.PASS,
    )
    return InspectionEvidence("top", 99, datetime(2026,9,1,12,1), "replay://new", position, "simulated", "cal", 1, 480, measurement)


def test_new_evidence_uses_persisted_position_aware_history(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(tmp_path / "test.db")); initialize(); initialize_evidence_store()
    session_id = _session(); _trusted(session_id, 10.0, 48.00)
    result = assess_evidence_temporally(session_id, "belt", _evidence(10.5, 48.08), _policy())
    assert result.status == TemporalQualityStatus.DEGRADED
    assert result.position_delta_ft == pytest.approx(0.5)
    assert result.width_change_per_ft == pytest.approx(0.16)


def test_lane_history_does_not_cross_contaminate(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(tmp_path / "test.db")); initialize(); initialize_evidence_store()
    session_id = _session(); _trusted(session_id, 10.0, 48.00, lane="belt-a")
    result = assess_evidence_temporally(session_id, "belt-b", _evidence(11.0, 48.02), _policy())
    assert result.status == TemporalQualityStatus.INSUFFICIENT_HISTORY
