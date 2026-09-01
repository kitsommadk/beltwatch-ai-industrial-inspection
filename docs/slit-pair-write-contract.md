# Slit pair write contract

`save_evidence_batch(session_id, writes)` accepts one or more `EvidenceWrite` objects and persists them through one database connection/transaction. The function rejects an empty batch and validates each lane ID. Any SQLite constraint error, child-record error or validation error causes the context manager to roll back the transaction.

`save_evidence` remains available and delegates to a one-item batch, so existing single-belt callers retain their response shape and persistence behavior.