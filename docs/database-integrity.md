# Database integrity boundary

BeltWatch uses SQLite for local-first pilot persistence. The database layer now makes path selection and schema compatibility explicit so different launch contexts cannot silently use different files or incompatible schemas.

## Stable path resolution

`BELTWATCH_DB_PATH` may be absolute or relative. Absolute paths are used directly. Relative paths are resolved against the backend directory rather than the process working directory. This prevents a service launcher, Docker working directory, test runner, or shell location from accidentally selecting a second database with the same filename.

The default remains `backend/beltwatch.db`.

## Foreign-key enforcement

Every BeltWatch SQLite connection executes `PRAGMA foreign_keys = ON`. SQLite does not reliably enforce declared foreign keys unless that connection-level setting is enabled. This protects evidence and event records from referencing nonexistent sessions.

## Transaction behavior

Successful context-managed database operations commit. Exceptions trigger an explicit rollback before the connection closes.

## Schema metadata

The database contains a singleton `schema_metadata` row. The application currently expects schema version `1`. Startup fails closed if the stored version differs from the application version instead of guessing how to interpret a changed schema.

This is deliberately a small migration foundation, not a full migration framework. A future schema change should introduce an explicit tested migration path and then increment `CURRENT_SCHEMA_VERSION`.

## Truth boundary

These checks improve software and persistence integrity. They do not validate camera hardware, physical measurement accuracy, model performance, plant network configuration, storage endurance, backup policy, or production disaster recovery.