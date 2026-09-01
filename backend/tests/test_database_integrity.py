from pathlib import Path

import pytest

from app import database


def test_default_database_path_is_absolute(monkeypatch):
    monkeypatch.delenv("BELTWATCH_DB_PATH", raising=False)
    assert database.db_path().is_absolute()
    assert database.db_path().name == "beltwatch.db"


def test_relative_database_path_is_anchored_to_backend(monkeypatch):
    monkeypatch.setenv("BELTWATCH_DB_PATH", "state/pilot.db")
    assert database.db_path() == (database.BACKEND_ROOT / "state/pilot.db").resolve()


def test_absolute_database_path_is_preserved(monkeypatch, tmp_path):
    target = tmp_path / "beltwatch.db"
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(target))
    assert database.db_path() == target.resolve()


def test_connect_enables_foreign_keys_and_creates_parent(monkeypatch, tmp_path):
    target = tmp_path / "nested" / "beltwatch.db"
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(target))

    with database.connect() as con:
        enabled = con.execute("PRAGMA foreign_keys").fetchone()[0]

    assert enabled == 1
    assert target.parent.exists()


def test_initialize_records_schema_version(monkeypatch, tmp_path):
    target = tmp_path / "beltwatch.db"
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(target))

    database.initialize()

    assert database.schema_version() == database.CURRENT_SCHEMA_VERSION
    assert database.foreign_keys_enabled() is True


def test_initialize_fails_closed_on_schema_version_mismatch(monkeypatch, tmp_path):
    target = tmp_path / "beltwatch.db"
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(target))
    database.initialize()

    with database.connect() as con:
        con.execute("UPDATE schema_metadata SET schema_version=99 WHERE singleton_id=1")

    with pytest.raises(RuntimeError, match="explicit migration is required"):
        database.initialize()
