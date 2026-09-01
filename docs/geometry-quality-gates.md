# Geometry quality gates

BeltWatch now separates **dimensional tolerance** from **image-geometry quality**. A width can be numerically within tolerance while the image evidence used to derive that width is too ambiguous to trust.

## Quality states

Automatic geometry is classified as:

- `high-confidence`: the configured image-geometry quality gates are satisfied;
- `degraded`: the result is still structurally valid, but one or more high-confidence requirements were missed;
- `invalid`: minimum validity requirements were not satisfied.

The current deterministic baseline uses two signals that are already available from the multi-row estimator:

- number of valid sampled rows;
- cross-row span spread in pixels.

This is intentionally a small software-validation contract. Future providers can add edge-position spread, contrast, segmentation confidence, calibration validity, blur, or other measured quality signals.

## Fail-closed automatic capture

`EvidenceService.capture_width_auto()` requires high-confidence geometry by default. If geometry is degraded or invalid, it raises a `GeometryQualityError` before dimensional classification and persistence.

This prevents a visually ambiguous frame from quietly becoming a `PASS` simply because its estimated width happens to be close to target.

Diagnostic workflows may explicitly set `require_high_confidence=False`. When they do, degraded provenance is retained and must remain visibly labeled as degraded; this is not the normal inspection path.

## Replay policy

The generated replay runtime uses `replay-multirow-quality-v1`:

- five valid rows are required for high-confidence;
- three valid rows are the minimum structurally valid result;
- up to 2 px cross-row span spread is high-confidence;
- more than 12 px spread is invalid.

These values are software regression thresholds, not manufacturing acceptance criteria or physical metrology tolerances.

## Persistence and migration

Evidence-store schema version 3 persists:

- quality policy ID;
- quality status;
- structured quality reasons.

A version-2 evidence store is migrated additively to version 3 by adding those fields to `inspection_geometry`. Historical version-2 geometry remains valid but has unknown historical quality because the quality gate did not exist when those rows were created. Unknown evidence schema versions still fail closed.

## Validation boundary

A high-confidence replay result means only that the generated/replayed image satisfied the configured software geometry-quality policy. It does **not** prove physical camera alignment, lens behavior, lighting, motion blur, vibration, calibration accuracy, edge-PC stability, plant conditions, or production readiness.
