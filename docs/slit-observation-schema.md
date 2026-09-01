# Shared slit observation schema v1

`slit_observations` uses `(session_id, camera_id, frame_sequence)` as the unique shared-frame identity and references the exact Belt A/B evidence rows. It stores the shared footage position and pixel-space pair diagnostics.

The schema is versioned independently so future changes—such as calibrated pair geometry or additional identity-confidence fields—must use explicit migrations rather than silently changing historical meaning.
