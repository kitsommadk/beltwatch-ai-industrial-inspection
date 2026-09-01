# Hardware-free validation

BeltWatch can continue meaningful engineering work before the physical cameras are available. This track validates software contracts and regression behavior without representing replayed data as live plant inspection.

## Modes and truth labels

- `simulation`: generated metadata/measurements used for workflow development.
- `replay`: finite or looping curated frames used for deterministic regression and algorithm evaluation.
- `pilot`: reserved for physically connected, validated camera providers. It remains fail-closed until hardware validation is complete.

Replay must never be labeled live camera data in the UI, API, logs, evidence records, or portfolio claims.

## What replay can validate

Replay can exercise frame sequencing, timestamps, payload provenance, stale-feed behavior, calibration math, edge/width algorithms, evidence persistence, API behavior, frontend rendering, model inference, latency measurements, and regression tests. A looping fixture can also support software soak tests.

## What replay cannot validate

Replay cannot establish USB bandwidth, actual negotiated UVC modes, cable stability, camera exposure, motion blur, real lighting uniformity, lens distortion, mounting vibration, thermal behavior of the physical camera, or real top/bottom device identity.

## Fixture policy

Public repository fixtures must be synthetic, generated, openly licensed for redistribution, or sanitized and explicitly approved for public use. Proprietary customer/work-order imagery must not be committed. Internal pilot imagery should remain in an approved private/local dataset location.

## Next hardware-free gates

1. Add a generated belt-frame fixture set covering nominal, narrow, wide, edge shift, and surface anomaly cases.
2. Implement a deterministic edge-span estimator against image payloads.
3. Feed estimator output into `EvidenceService` instead of caller-supplied pixel spans.
4. Add calibration verification fixtures and known expected measurements.
5. Add replay benchmark reporting for false alarms, misses, latency, and throughput.
6. Add optional prerecorded video-file ingestion using the same OpenCV capture boundary.

The goal is to arrive at physical-camera day with the software pipeline, evidence model, UI, and evaluation harness already exercised. Hardware validation then verifies the remaining physical assumptions rather than beginning software integration from scratch.
