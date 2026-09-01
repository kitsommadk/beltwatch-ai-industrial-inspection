# Temporal width quality

BeltWatch evaluates sequential width measurements for temporal consistency after frame and geometry quality checks have established that the current image-derived measurement is individually trustworthy.

The deterministic baseline compares the current measured width with both the immediately previous trusted width and the median of a bounded recent history window. A measurement can be high-confidence, degraded, or invalid.

This layer is intended to surface sudden discontinuities that can be caused by image instability, vibration, intermittent geometry errors, or a real physical width change. It must not erase or smooth away a real defect. Invalid or degraded temporal evidence should be surfaced for review rather than silently replaced with a historical value.

## Validation boundary

The current thresholds are software/replay regression values only. They are not manufacturing tolerances and are not physically validated limits for belt-width rate of change. Physical qualification must consider belt speed, frame cadence, camera exposure, mounting vibration, calibration uncertainty, material behavior, and the smallest real defect BeltWatch is expected to preserve.

A future pilot policy should express rate-of-change against physical position or elapsed time rather than relying only on adjacent samples. The operator remains authoritative, and this layer does not control the machine.
