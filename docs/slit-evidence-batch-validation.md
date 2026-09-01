# Batch validation behavior

Lane IDs are validated inside the transaction before their record is inserted. If a later `EvidenceWrite` has an invalid lane ID, the raised exception exits the transaction context and rolls back any earlier records from that batch. SQLite constraints provide the same rollback behavior for duplicate identity or invalid child data.