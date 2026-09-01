# Pair diagnostics relationship

Gap, centers, center distance and total occupied span are still derived from the same estimator result as the lane evidence. They are returned only after the lane batch succeeds, but they are not part of the SQLite transaction because they are not yet persisted. A future shared-observation schema should add them without duplicating values per lane.