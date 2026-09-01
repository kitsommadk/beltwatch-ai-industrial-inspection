# Architecture

`two-lane frame` → `multi-lane estimator` → `independent A/B evidence` → `atomic A/B evidence persistence` → `shared observation persistence` → `audit/API`.

The shared observation references the exact persisted lane records rather than re-running CV (computer vision) or recalculating pair geometry from a second frame.
