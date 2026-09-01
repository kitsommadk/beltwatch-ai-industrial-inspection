# Dataset and provider contracts

BeltWatch now separates two concerns that will matter when representative imagery and trained models arrive: **which algorithm is selected** and **which data is allowed to influence that algorithm's evaluation**.

## Span provider registry

`backend/app/span_registry.py` is the configuration boundary for belt-edge geometry providers. Current names are:

- `scanline` — single-row deterministic development baseline.
- `multirow` — multi-row deterministic provider that has passed the generated synthetic robustness gate.
- `opencv-contour` — optional OpenCV contour provider that has passed the generated synthetic robustness gate.

Provider selection is explicit. An unknown name raises a configuration error; BeltWatch does not silently substitute another estimator. Optional CV dependencies are imported lazily so the core FastAPI application remains lightweight.

The registry metadata describes the provider family and current validation stage. A validation-stage label is not a production qualification claim. `synthetic-robustness` means only that the provider met the repository's generated-image tests.

## Representative-image dataset manifest

`backend/app/dataset_manifest.py` defines metadata for future sanitized image collections without putting proprietary images or production identifiers in the public repository.

Each record identifies:

- a sanitized asset reference;
- a synthetic/non-identifying physical run ID;
- train, validation, test, or frozen holdout split;
- normal, defect, or unknown surface label;
- camera identity and calibration version;
- lighting, material, and speed profiles;
- optional defect labels and notes.

### Leakage prevention

Frames from one physical belt/run are strongly correlated. Splitting adjacent frames from the same run across training and test sets would let a model see nearly the same scene during both learning and evaluation, producing misleading benchmark results.

`validate_split_isolation()` therefore rejects any manifest where one `physical_run_id` occurs in more than one dataset split.

## Public-repository boundary

Do not commit customer names, customer IDs, work orders, plant names/layouts, proprietary product data, production records, credentials, raw proprietary images/video, or trained weights derived from non-public data.

The public repository may contain schema examples and generated/sanitized fixtures. Representative production imagery should remain in an approved private storage location and be referenced through sanitized manifest identifiers.

## Next promotion step

Before selecting a trained production model, populate a representative private manifest and run each candidate provider/model against the same frozen test/holdout data. Selection should be based on measured accuracy, miss rate, false alarms per footage unit, latency, and edge-PC resource use rather than model popularity.
