# BeltWatch AI — Model Evaluation Protocol

## Purpose
BeltWatch will not select a production vision model based on popularity or a single demo. Candidate models must be measured on representative belt imagery and the actual target edge hardware.

## Candidate tracks

### Known-defect detection / segmentation
Use labeled examples for defect classes where localization matters, such as edge damage, tears, punctures, splice/lacing irregularities, and surface damage.

Candidate deployment path: train in a supported framework, export to ONNX/OpenVINO, then benchmark locally.

### Industrial anomaly detection
Use mostly normal/acceptable belt imagery to learn the expected visual distribution and score unusual regions. This is especially useful while rare defect classes have few labeled examples.

## Dataset rules
- Keep customer/proprietary imagery out of the public repository.
- Split train/validation/test by physical belt or inspection run, not random adjacent frames.
- Record camera ID, lighting setup, calibration version, belt material/color, speed, surface side, and position metadata.
- Deduplicate near-identical sequential frames when building evaluation sets.
- Preserve a frozen holdout set that is never used for threshold tuning.

## Required metrics

### Detection quality
- precision
- recall
- false positives per 1,000 ft inspected
- missed critical defects
- localization/segmentation quality where applicable
- performance by defect class and belt condition

### Anomaly quality
- image-level and region-level precision/recall
- false alarms per 1,000 ft inspected
- threshold sensitivity
- performance on lighting/material shifts

### Edge performance
- median and p95 inference latency
- sustained frames per second
- CPU/GPU/NPU utilization where available
- RAM usage
- thermal throttling observations
- startup time
- recovery after camera/model restart

## Safety / deployment gate
A model remains `experimental` until it passes a documented evaluation run. BeltWatch remains operator-assistive: detections create reviewable events and do not directly control machinery.

## Model registry record
Every benchmarked artifact should record:
- model family/version
- training dataset version
- export format and precision
- preprocessing size
- threshold(s)
- hardware/runtime
- evaluation dataset version
- metric results
- benchmark date
- disposition: rejected / experimental / pilot candidate

## Current deployment research
OpenVINO remains a useful benchmark target for Intel edge systems because current Ultralytics export paths support OpenVINO inference across Intel CPU/GPU/NPU targets. Actual BeltWatch hardware capabilities must be measured rather than assumed.
