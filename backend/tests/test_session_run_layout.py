import sqlite3
from pathlib import Path

from fastapi.testclient import TestClient


def test_session_defaults_to_single_layout(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(tmp_path / "single.db"))
    monkeypatch.setenv("BELTWATCH_INSPECTION_MODE", "simulation")

    from app.main import app, get_runtime

    get_runtime.cache_clear()
    with TestClient(app) as client:
        started = client.post(
            "/api/session/start",
            json={
                "roll_number": "R1",
                "work_order": "WO1",
                "operator": "tester",
                "target_width_in": 48,
                "tolerance_in": 0.08,
                "target_length_ft": 1000,
            },
        )
        assert started.status_code == 200
        assert started.json()["run_layout"] == "single"
        assert client.get("/api/session").json()["run_layout"] == "single"


def test_slitting_session_persists_two_lane_layout(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(tmp_path / "slit.db"))
    monkeypatch.setenv("BELTWATCH_INSPECTION_MODE", "simulation")

    from app.main import app, get_runtime

    get_runtime.cache_clear()
    with TestClient(app) as client:
        started = client.post(
            "/api/session/start",
            json={
                "roll_number": "R-SLIT",
                "work_order": "WO-SLIT",
                "operator": "tester",
                "target_width_in": 24,
                "tolerance_in": 0.08,
                "target_length_ft": 1000,
                "run_layout": "slit-two-lane",
            },
        )
        assert started.status_code == 200
        assert started.json()["run_layout"] == "slit-two-lane"


def test_invalid_layout_is_rejected(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(tmp_path / "invalid.db"))
    monkeypatch.setenv("BELTWATCH_INSPECTION_MODE", "simulation")

    from app.main import app, get_runtime

    get_runtime.cache_clear()
    with TestClient(app) as client:
        response = client.post(
            "/api/session/start",
            json={
                "roll_number": "R1",
                "work_order": "WO1",
                "operator": "tester",
                "target_width_in": 48,
                "tolerance_in": 0.08,
                "target_length_ft": 1000,
                "run_layout": "two-belts-always",
            },
        )
        assert response.status_code == 422


def test_schema_v1_migrates_existing_sessions_to_single(tmp_path: Path, monkeypatch):
    path = tmp_path / "legacy.db"
    con = sqlite3.connect(path)
    con.executescript(
        """
        CREATE TABLE schema_metadata (
            singleton_id INTEGER PRIMARY KEY CHECK(singleton_id = 1),
            schema_version INTEGER NOT NULL CHECK(schema_version > 0)
        );
        INSERT INTO schema_metadata(singleton_id, schema_version) VALUES (1, 1);
        CREATE TABLE sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            roll_number TEXT NOT NULL,
            work_order TEXT NOT NULL,
            operator TEXT NOT NULL,
            target_width_in REAL NOT NULL,
            tolerance_in REAL NOT NULL,
            target_length_ft REAL NOT NULL,
            footage_ft REAL NOT NULL DEFAULT 0,
            current_width_in REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'ready',
            started_at TEXT,
            updated_at TEXT NOT NULL
        );
        INSERT INTO sessions(roll_number,work_order,operator,target_width_in,tolerance_in,target_length_ft,
            footage_ft,current_width_in,status,updated_at)
        VALUES ('legacy','legacy','tester',48,0.1,1000,0,48,'complete','now');
        CREATE TABLE events (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id INTEGER NOT NULL,
            created_at TEXT NOT NULL,
            damage_type TEXT NOT NULL,
            severity TEXT NOT NULL,
            camera TEXT NOT NULL,
            location_ft REAL NOT NULL,
            measured_width_in REAL NOT NULL,
            confidence REAL NOT NULL,
            status TEXT NOT NULL DEFAULT 'open',
            review_note TEXT NOT NULL DEFAULT '',
            reviewed_at TEXT,
            FOREIGN KEY(session_id) REFERENCES sessions(id)
        );
        CREATE TABLE audit_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            action TEXT NOT NULL,
            detail TEXT NOT NULL
        );
        """
    )
    con.commit(); con.close()

    monkeypatch.setenv("BELTWATCH_DB_PATH", str(path))
    from app.database import connect, initialize, schema_version

    initialize()
    assert schema_version() == 2
    with connect() as migrated:
        row = migrated.execute("SELECT run_layout FROM sessions WHERE roll_number='legacy'").fetchone()
        assert row["run_layout"] == "single"
