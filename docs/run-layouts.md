# Run layouts

BeltWatch does not assume every inspection contains two belts.

## Single-belt run

Use the `single` layout when one belt is passing through the inspection area. The active lane ID is `belt`.

## Slit two-lane run

Use the `slit-two-lane` layout only when a wider belt is being slit into two narrower belts that travel side-by-side. The active lane IDs are `belt-a` and `belt-b`.

The initial deterministic replay convention assigns Belt A to the left-most detected belt in image coordinates and Belt B to the right-most. This is an identity convention for software validation, not a physically qualified tracking rule. Live pilot validation must confirm camera orientation, belt crossover impossibility, occlusion behavior, and lane identity persistence.

Two-lane mode fails closed if exactly two plausible belt spans are not present. It must not silently downgrade a slit run into single-belt mode, because doing so could hide a missing or merged lane. Likewise, single-belt runs should use the single-belt estimator rather than requiring artificial Belt A/B labels.

Future session setup should store the selected run layout explicitly so the runtime, evidence schema, temporal history, API, and UI all use the correct lane model for that run.
