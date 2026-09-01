# Edge sharpness quality gates

BeltWatch now records a hardware-independent edge-sharpness signal for automatic width geometry.

For each detected edge, the deterministic baseline examines adjacent-pixel intensity gradients in a small neighborhood around the threshold crossing. The weaker peak gradient from the left and right belt edges is retained. Multi-row estimation conservatively retains the weakest measurable row value.

This is intended to catch a failure mode that contrast alone cannot describe: an image may have adequate overall belt/background contrast while motion blur, defocus, vibration, or image processing spreads the transition over several pixels. In that condition the threshold crossing can still look geometrically stable while its exact location is less trustworthy.

Replay policy `replay-multirow-quality-v4` requires both contrast and sharpness evidence. The current generated-fixture thresholds are software regression values only:

- high-confidence edge sharpness: at least 80 intensity units per adjacent-pixel transition
- valid edge sharpness: at least 25 intensity units
- values below the valid threshold fail closed before dimensional PASS/WARNING/FAIL classification

These thresholds are **not** physical focus specifications, allowable motion blur, exposure settings, belt-speed limits, plant lighting requirements, or production acceptance criteria.

Physical validation must characterize the actual camera, lens, exposure, lighting, belt speed, vibration, mounting, material, and edge appearance. A future physical sharpness policy should be derived from repeatability and metrology error on representative runs rather than copied from replay fixtures.
