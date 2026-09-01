# Single-belt compatibility

Single-belt evidence still uses the same `save_evidence(session_id, evidence, lane_id='belt', temporal=...)` call signature and returns one decoded record. Its implementation now benefits from the shared insertion path without changing the API's legacy raw-record response.