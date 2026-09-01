# Slit auto-capture API persistence contract

A successful `POST /api/evidence/capture-auto` during a `slit-two-lane` session returns exactly two lane records from one committed batch. The records retain independent lane IDs and results while sharing frame sequence and position.

If the evidence batch cannot commit, the endpoint does not have a valid persisted pair to return. Existing exception handling converts supported runtime/validation failures to HTTP 422; database integrity failures remain server errors and roll back the batch.