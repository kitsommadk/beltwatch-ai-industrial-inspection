# Acceptance criteria

- slit auto-capture persists exactly one shared observation referencing exact Belt A/B evidence IDs;
- shared camera, frame sequence and position are validated before insert;
- duplicate shared-frame observation identity is rejected;
- listing is scoped to the current session;
- single-belt auto capture remains backward compatible and creates no slit observation;
- foreign-key integrity remains clean;
- pair diagnostics remain explicitly pixel-space observations.
