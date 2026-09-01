# Slit observation ledger

A `slit-two-lane` auto capture now has a shared observation record in addition to the independent Belt A and Belt B evidence records.

The observation stores the shared session/camera/frame/position identity and deterministic pixel-space pair diagnostics: gap, Belt A/B centers, center distance and total occupied span. It references the exact Belt A and Belt B evidence IDs that produced the observation.

This creates a historical foundation for trending how the two slit products move relative to each other along footage without collapsing their independent width measurements.

These diagnostics remain observations only. They do not identify mechanical root cause, and pixel-space values are not physically qualified metrology until camera/calibration/slitter validation is completed.
