import sqlite3
from pathlib import Path

from app.calibration import SimulatedPositionProvider, make_calibration_profile
from app.camera import SimulatedCamera
from app.database import initialize
from app.evidence import EvidenceService
from app.evidence_store import initialize_evidence_store, list_evidence, save_evidence


def _session():
    from app.database import connect
    with connect() as con:
        c=con.execute("""INSERT INTO sessions(roll_number,work_order,operator,target_width_in,tolerance_in,target_length_ft,footage_ft,current_width_in,status,updated_at)
        VALUES ('R1','WO1','tester',48,0.1,1000,0,48,'inspecting','now')""")
        return c.lastrowid


def _service():
    cal=make_calibration_profile('top-cal-v1','top',1,960,48)
    return EvidenceService(SimulatedCamera('top'),SimulatedPositionProvider(start_ft=100),cal)


def test_same_frame_can_persist_belt_a_and_b(monkeypatch,tmp_path:Path):
    monkeypatch.setenv('BELTWATCH_DB_PATH',str(tmp_path/'test.db')); initialize(); initialize_evidence_store(); sid=_session()
    evidence=_service().capture_width(960,48,0.1,0.2)
    a=save_evidence(sid,evidence,lane_id='belt-a'); b=save_evidence(sid,evidence,lane_id='belt-b')
    assert a['frame_sequence']==b['frame_sequence']==1
    assert a['lane_id']=='belt-a' and b['lane_id']=='belt-b'
    assert {r['lane_id'] for r in list_evidence(sid)}=={'belt-a','belt-b'}


def test_same_lane_same_frame_remains_duplicate(monkeypatch,tmp_path:Path):
    monkeypatch.setenv('BELTWATCH_DB_PATH',str(tmp_path/'test.db')); initialize(); initialize_evidence_store(); sid=_session()
    evidence=_service().capture_width(960,48,0.1,0.2); save_evidence(sid,evidence,lane_id='belt-a')
    try:
        save_evidence(sid,evidence,lane_id='belt-a'); assert False
    except sqlite3.IntegrityError: pass


def test_default_lane_preserves_single_belt_behavior(monkeypatch,tmp_path:Path):
    monkeypatch.setenv('BELTWATCH_DB_PATH',str(tmp_path/'test.db')); initialize(); initialize_evidence_store(); sid=_session()
    row=save_evidence(sid,_service().capture_width(960,48,0.1,0.2))
    assert row['lane_id']=='belt'
