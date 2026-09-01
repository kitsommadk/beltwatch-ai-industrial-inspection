# Error semantics

Validation/runtime errors already handled by the slit endpoint remain HTTP 422 responses. Raw SQLite integrity failures are intentionally not converted into a false successful capture; they propagate as server errors while the database transaction rolls back. A later API-hardening pass can map storage failures to a stable service error without weakening rollback.