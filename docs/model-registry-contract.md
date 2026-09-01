# Model evaluation registry contract

BeltWatch separates **model existence** from **model qualification**. A model file or successful demo is not enough to call a model production-ready.

`backend/app/model_registry.py` records immutable model/version identities, the dataset manifest used for evaluation, runtime and hardware targets, measured evaluation metrics, and an explicit disposition.

## Dispositions

- `experimental` — valid for research and comparison, but not promoted.
- `pilot-candidate` — passed defined evaluation gates strongly enough to justify controlled pilot validation. This is not production qualification.
- `rejected` — failed one or more required gates or is otherwise unsuitable for the current deployment target.

`pilot-candidate` and `rejected` records require explicit reasons so promotion decisions cannot be hidden behind a status label.

## Identity and reproducibility

Each record identifies:

- model ID and immutable version;
- task family: anomaly, detection, or segmentation;
- training/inference framework;
- private or otherwise approved artifact reference;
- dataset manifest ID;
- runtime target such as ONNX Runtime or OpenVINO;
- hardware target such as the intended edge CPU.

The same model/version pair cannot be silently overwritten in one registry instance. A new artifact or evaluation state should receive a new version or a new persisted evaluation record once persistence is added.

## Minimum evaluation fields

The current contract records cases, misses, false alarms, mean latency, throughput, optional precision/recall, false alarms per 1,000 ft, and peak memory. These are deliberately deployment-oriented metrics rather than only machine-learning leaderboard scores.

Future evaluation runs should also capture thermal behavior, CPU utilization, recovery after dropped frames, per-defect recall, localization quality, and confidence calibration when those measurements become available.

## Promotion rule

No trained model should become BeltWatch's default provider because it is newer, popular, or performs well on one sample. Promotion to `pilot-candidate` should require:

1. a representative, leakage-controlled test/holdout manifest;
2. acceptable critical-miss performance;
3. acceptable false-alarm rate per footage unit;
4. acceptable latency/throughput on the intended edge hardware;
5. acceptable resource and thermal behavior;
6. explicit human review of failure cases.

Physical-camera validation remains a separate later gate. Hardware-free evaluation can reduce software/model risk but cannot validate optics, lighting, motion blur, vibration, USB transport, or physical calibration accuracy.

## Public repository boundary

Do not commit proprietary images, production identifiers, customer data, credentials, or trained weights derived from non-public data. The registry may contain sanitized metadata and example records, while model artifacts and representative imagery remain in approved private storage.
