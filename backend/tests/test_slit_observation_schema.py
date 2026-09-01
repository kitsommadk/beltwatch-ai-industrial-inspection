from app.database import connect, initialize
from app.evidence_store import initialize_evidence_store
from app.slit_observation_store import SLIT_OBSERVATION_SCHEMA_VERSION, initialize_slit_observation_store


def test_slit_observation_schema_initializes_with_foreign_keys_clean(tmp_path, monkeypatch):
    monkeypatch.setenv("BELTWATCH_DB_PATH", str(tmp_path / "beltwatch.db"))
    initialize(); initialize_evidence_store(); initialize_slit_observation_store()
    with connect() as con:
        version=con.execute("SELECT schema_version FROM slit_observation_schema_metadata WHERE singleton_id=1").fetchone()[0]
        assert version == SLIT_OBSERVATION_SCHEMA_VERSION == 1
        columns={row["name"] for row in con.execute("PRAGMA table_info(slit_observations)")}
        assert {"session_id","camera_id","frame_sequence","position_ft","belt_a_evidence_id","belt_b_evidence_id","gap_px","belt_a_center_x_px","belt_b_center_x_px","center_distance_px","total_occupied_span_px"} <= columns
        assert con.execute("PRAGMA foreign_key_check").fetchall() == []
