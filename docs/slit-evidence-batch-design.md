# Slit evidence batch design

`EvidenceWrite` packages the lane evidence, lane identity and optional temporal assessment needed for one persistence operation. `_insert_evidence` performs the parent and child inserts using a caller-owned SQLite connection. `save_evidence_batch` owns the transaction and decodes the committed records for the API.

Keeping transaction ownership outside the per-record insert is what allows two lanes to share one rollback boundary.