import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


def db_path() -> Path:
    return Path(os.getenv("BELTWATCH_DB_PATH", Path(__file__).parents[1] / "beltwatch.db"))


@contextmanager
def connect():
    connection = sqlite3.connect(db_path())
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def initialize() -> None:
    db_path().parent.mkdir(parents=True, exist_ok=True)
    with connect() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS sessions (
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

            CREATE TABLE IF NOT EXISTS events (
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

            CREATE TABLE IF NOT EXISTS audit_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                action TEXT NOT NULL,
                detail TEXT NOT NULL
            );
            """
        )

