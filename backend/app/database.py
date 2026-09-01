import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path


BACKEND_ROOT = Path(__file__).resolve().parents[1]
CURRENT_SCHEMA_VERSION = 1


def db_path() -> Path:
    """Return a stable absolute SQLite path.

    A relative BELTWATCH_DB_PATH is resolved against the backend directory rather
    than the process working directory so Docker, tests, and service launchers do
    not accidentally point BeltWatch at different databases.
    """
    configured = os.getenv("BELTWATCH_DB_PATH")
    path = Path(configured).expanduser() if configured else BACKEND_ROOT / "beltwatch.db"
    if not path.is_absolute():
        path = BACKEND_ROOT / path
    return path.resolve()


@contextmanager
def connect():
    path = db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def foreign_keys_enabled() -> bool:
    with connect() as con:
        return bool(con.execute("PRAGMA foreign_keys").fetchone()[0])


def schema_version() -> int | None:
    with connect() as con:
        row = con.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='schema_metadata'"
        ).fetchone()
        if row is None:
            return None
        version = con.execute(
            "SELECT schema_version FROM schema_metadata WHERE singleton_id=1"
        ).fetchone()
        return int(version[0]) if version is not None else None


def initialize() -> None:
    with connect() as con:
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_metadata (
                singleton_id INTEGER PRIMARY KEY CHECK(singleton_id = 1),
                schema_version INTEGER NOT NULL CHECK(schema_version > 0)
            );

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
        con.execute(
            "INSERT OR IGNORE INTO schema_metadata(singleton_id, schema_version) VALUES (1, ?)",
            (CURRENT_SCHEMA_VERSION,),
        )
        stored = con.execute(
            "SELECT schema_version FROM schema_metadata WHERE singleton_id=1"
        ).fetchone()[0]
        if stored != CURRENT_SCHEMA_VERSION:
            raise RuntimeError(
                f"database schema version {stored} does not match application version {CURRENT_SCHEMA_VERSION}; "
                "explicit migration is required"
            )
