# Atomic slit evidence data model

The database continues to store Belt A and Belt B as separate `inspection_evidence` rows because each lane has an independent target and measurement result. Shared observation identity is represented by matching session, camera, frame sequence and position, while `lane_id` differentiates the products.

Atomicity changes the write boundary, not the normalized lane-aware schema.