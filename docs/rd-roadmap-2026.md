# BeltWatch AI — 2026 R&D Roadmap

## Objective
Advance the current synthetic local-first pilot into a validated industrial inspection system while keeping the operator authoritative and the system observation-only.

## Near-term gateway
Before choosing a production vision model, complete:

1. live camera ingestion prototype
2. calibration and belt-width measurement prototype
3. sanitized baseline image collection plan
4. repeatable model evaluation harness

## Development tracks

### Camera ingestion
Create a swappable camera adapter for USB/UVC first, with capture timestamps, top/bottom camera identity, FPS/health status, dropped-frame handling, reconnect logic, and stale-feed detection.

### Position synchronization
Create a linear-position source abstraction. Start with software/simulated footage position and leave a read-only boundary for a future encoder or PLC source. Persist frame-to-position mapping so every event can be traced to a physical location on the belt.

### Calibration and width measurement
Store versioned calibration profiles, pixel-to-inch/mm conversion, both-edge detection, continuous width measurement, confidence, tolerance state, and a pre-run calibration verification step.

### AI strategy
Benchmark two complementary paths rather than committing early to one model family:

- supervised detection/segmentation for known defect classes
- visual anomaly detection for rare or unseen defects

Candidate deployment stack includes OpenVINO or ONNX Runtime for Intel edge inference, anomalib for industrial anomaly detection, and Ultralytics detection/segmentation models for labeled defect classes.

### Dataset and evaluation
Build a sanitized dataset schema. Capture defect-free baseline images first, then known defects as they become available. Split train/validation/test by physical belt or run to reduce leakage. Track lighting, camera, calibration, speed, material, and surface metadata.

Measure precision, recall, misses, false alarms per footage unit, localization quality, inference latency, throughput, CPU/RAM utilization, and stability across lighting/speed changes.

### Evidence and operator feedback
Store local event snapshots/clips with configurable retention. Preserve acknowledge/false-positive review and add defect taxonomy, severity, and notes. Reviewed events may become curated training/evaluation candidates, but production should not retrain itself automatically.

### Reliability and security
Add structured logs, health metrics, restart-safe sessions, disk safeguards, authentication/RBAC, HTTPS for plant-LAN use, and outbound-only synchronization for future remote access.

## Research notes
- Anomalib remains a strong candidate for benchmarking industrial anomaly detection and supports OpenVINO-oriented deployment workflows.
- Ultralytics models can be exported to ONNX/OpenVINO for CPU/GPU/NPU deployment.
- OpenVINO 2026 supports Intel NPU devices on Core Ultra platforms; the selected BeltWatch edge PC hardware should be benchmarked before assuming NPU availability.

## Decision rule
Production model selection will be based on measured image quality, defect data availability, false-positive rate, latency, and edge-PC performance—not popularity of a specific model family.
