# Contrast quality gates

BeltWatch now treats visual separation between the detected belt and its local background as a first-class geometry-quality signal.

## Signal

For each valid scan row, the deterministic estimator samples a three-pixel window immediately inside and outside both detected belt edges. It computes the local intensity transition on the left and right and retains the weaker transition as that row's edge contrast.

The multi-row estimator persists the minimum measurable edge contrast across all valid rows as `min_edge_contrast`. Using the weakest supported edge prevents one strong side or one strong row from hiding a poorly separated edge elsewhere.

## Replay policy

`replay-multirow-quality-v3` currently requires:

- at least 80 intensity units for high-confidence contrast;
- at least 30 intensity units for basic validity.

A result between those values is degraded. A result below the valid minimum is invalid. The normal automatic evidence path already fails closed on degraded or invalid geometry.

These thresholds are software/replay regression values only. They are not plant lighting specifications, camera exposure requirements, customer acceptance criteria, or physical metrology tolerances.

## Persistence

Evidence schema version 5 adds `min_edge_contrast` to `inspection_geometry`. The migration from v4 to v5 is additive and preserves prior evidence; older records may have no historical contrast value.

## Physical validation boundary

Real-camera contrast depends on lens selection, exposure, gain, controlled lighting, material color/texture, contamination, shadows, motion blur, mounting, and background design. Those factors remain part of later physical-camera validation. A high replay contrast score does not qualify a production camera setup.
