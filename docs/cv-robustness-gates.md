# BeltWatch generated CV robustness gates

BeltWatch now has a hardware-free robustness suite for comparing belt-edge providers before representative physical-camera imagery is available.

## Purpose

The suite answers a narrow question: can a provider preserve known belt geometry when synthetic image conditions are deliberately degraded?

It does **not** validate production metrology, lens calibration, motion blur, vibration, real conveyor backgrounds, surface reflectivity, USB transport, or physical lighting.

## Current generated cases

- clean nominal belt
- shifted and narrower belt
- left-to-right brightness gradient
- deterministic impulse noise
- localized shadow band
- upper left edge notch
- lower right edge notch

Each fixture stores ground-truth left and right pixel coordinates so providers are scored against the same answer.

## Current promotion gates

For `OpenCVContourEstimator` on the generated suite:

- success rate: 100%
- mean absolute span error: <= 2 px
- maximum absolute span error: <= 6 px
- mean edge error: <= 2 px

For `MultiRowDarkEstimator`:

- success rate: at least 6/7 cases
- mean absolute span error: <= 3 px

These thresholds are development gates only. They are not customer acceptance tolerances.

## Why this matters

A provider should not be selected because it looks visually impressive on one image. BeltWatch keeps the provider boundary fixed and changes only the algorithm, allowing the same replay cases, ground truth, metrics, and downstream evidence pipeline to be reused.

## Next gate

The next dataset stage should use sanitized representative images captured from the intended camera/lighting geometry. Those images should be separated by physical run and should include lighting variation, material variation, belt edges, surface texture, blur, and realistic background clutter. Generated results remain labeled synthetic even if performance is perfect.
