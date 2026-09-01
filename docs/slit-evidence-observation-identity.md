# Shared slit observation identity

For the current pilot, a shared two-lane observation is identified operationally by session ID, camera ID, frame sequence and position. Belt A and Belt B are lane-specific children of that observation in meaning, although the current schema stores the shared identity redundantly on both evidence rows.

A future shared-observation table can normalize this relationship when pair diagnostics are persisted.