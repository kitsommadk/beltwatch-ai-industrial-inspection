# Replay runtime mode

BeltWatch now has an explicit `replay` inspection mode in addition to `simulation`.

## Why replay exists

Simulation exercises workflow state and persistence but does not provide image payloads. Replay feeds deterministic image-shaped payloads through the same camera -> span estimator -> calibration -> width evidence path intended for future live cameras.

Replay is hardware-free validation. It is not a live-camera or production claim.

## Modes

- `simulation` — generated metadata/workflow behavior. Caller-supplied span capture remains available for compatibility.
- `replay` — finite deterministic image sequence with automatic span estimation and traceable `replay://` provenance.
- `pilot` — intentionally unavailable and fail-closed until physically validated camera/hardware providers are installed.

Set the runtime with `BELTWATCH_INSPECTION_MODE=replay`.

## Automatic capture

`POST /api/evidence/capture-auto` accepts only a camera identity (`top` or `bottom`). The caller does not provide `measured_span_px`.

The runtime captures the next replay frame, runs the configured `MultiRowDarkEstimator`, converts pixel span through the development calibration profile, samples belt position, and persists evidence through the existing evidence store.

The included generated replay sequence uses known widths around a 960 px / 48 in development reference so tests can verify that image geometry, rather than caller input, changes the resulting measurement.

## Finite fixture behavior

Each replay camera contains six frames and does not loop. Once exhausted, capture raises an end-of-fixture error and increments camera capture-failure health telemetry. Finite behavior makes regression runs bounded and makes exhaustion visible instead of silently recycling evidence.

## System status

`GET /api/system` now reports replay cameras as `replay` and includes camera health fields when supported: connection state, stale state, frames captured, capture failures, and last-frame timestamp. Storage status is reported as `not-measured` rather than a fabricated free-space percentage.

## Validation boundary

Replay can validate software integration, deterministic geometry behavior, provenance, error handling, and evidence persistence. It cannot validate USB bandwidth, camera identity, exposure, lighting, motion blur, optics, lens distortion, mounting vibration, physical calibration, edge-computer thermals, or plant performance.

Those remain physical pilot gates.