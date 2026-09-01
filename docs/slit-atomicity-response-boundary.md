# Response boundary

The API constructs the successful slit response only after `save_evidence_batch` returns committed lane records. Pair diagnostics are derived before persistence but attached to the response only when the evidence batch succeeds.