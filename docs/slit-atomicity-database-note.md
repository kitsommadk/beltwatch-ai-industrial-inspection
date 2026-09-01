# SQLite transaction note

BeltWatch's `connect()` context manager commits when the block exits successfully and rolls back on exceptions. `save_evidence_batch` intentionally performs all lane inserts inside one such context. A constraint error on a later lane propagates out of the block, triggering rollback of earlier inserts from the same batch.