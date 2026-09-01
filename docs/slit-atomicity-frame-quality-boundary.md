# Frame-quality boundary

The shared frame's quality result is currently duplicated into each lane's child record. The batch transaction ensures those duplicated lane records commit together. A future normalized shared-observation table may store shared frame quality once, but this change intentionally avoids a schema migration.