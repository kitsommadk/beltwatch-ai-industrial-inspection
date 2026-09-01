# Slit evidence atomicity

A `slit-two-lane` automatic capture represents one physical/replay frame and one position sample containing both Belt A and Belt B.

The persistence contract is therefore all-or-nothing: both lane evidence records and their geometry, frame-quality and temporal child records are written in one SQLite transaction. If any write fails, the transaction rolls back and neither lane remains in the evidence ledger.

Temporal assessment is calculated for both lanes before either current record is persisted. This keeps the comparison history scoped to prior trusted evidence and prevents the current shared frame from becoming its own history.

Audit records are still written after the evidence transaction commits. Pair diagnostics remain response-time pixel-space observations and are not yet persisted historically.

This improves evidence integrity but does not constitute physical camera or metrology validation.