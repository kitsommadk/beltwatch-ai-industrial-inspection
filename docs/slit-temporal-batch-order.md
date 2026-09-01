# Slit temporal batch ordering

Both Belt A and Belt B temporal assessments are computed before the current shared-frame pair is written. This ensures each assessment sees only prior trusted evidence for its own session, camera, lane and calibration profile/version.

The two resulting temporal assessments are then persisted alongside their corresponding lane evidence in the same batch transaction.