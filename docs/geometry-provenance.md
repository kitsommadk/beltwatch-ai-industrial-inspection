# Geometry provenance

Automatic BeltWatch width evidence now preserves the image-geometry result that produced the dimensional measurement instead of storing only the final pixel span.

## Persisted fields

For image-driven captures, the evidence record can be joined to `inspection_geometry`, which stores:

- a stable estimator ID;
- left belt edge in pixels;
- right belt edge as an exclusive pixel coordinate;
- representative row coordinate;
- estimator threshold;
- number of valid sampled rows;
- cross-row span spread in pixels.

The interval remains half-open: `[left_x, right_x_exclusive)`, so `measured_span_px = right_x_exclusive - left_x` without off-by-one ambiguity.

## Why this matters

A stored width such as `47.9 in` is not enough to reconstruct why the system produced that result. Geometry provenance lets an engineer or operator trace the measurement back through:

`frame -> estimator/version -> left/right edges -> pixel span -> calibration -> physical width -> tolerance status`

That makes later algorithm comparisons, regression analysis, and evidence review more defensible.

## Manual compatibility path

`POST /api/evidence/capture` still accepts a caller-supplied pixel span for development compatibility. Those records intentionally have no geometry-provenance row. A missing geometry record therefore means the dimensional span was not derived by the automatic image estimator.

`POST /api/evidence/capture-auto` remains the preferred replay/live-image path because the image drives the measurement.

## Evidence schema

The evidence persistence module now tracks `EVIDENCE_SCHEMA_VERSION = 2`. Version 2 adds `inspection_geometry` as a one-to-one child of `inspection_evidence`. Existing dimensional evidence is not rewritten; older rows remain valid with no geometry child row.

The geometry child uses a foreign key with `ON DELETE CASCADE`, so removing a parent evidence record cannot leave orphaned provenance.

## Validation boundary

The current replay estimator ID `multirow-dark-v1` describes the configured deterministic multi-row algorithm contract. It has hardware-free synthetic/replay validation only. Persisting its geometry does not make the measurement physical metrology or production-qualified.

Future physically validated providers and trained segmentation models should use their own stable estimator/model IDs and preserve equivalent provenance wherever the algorithm can produce meaningful edge geometry or confidence metadata.
