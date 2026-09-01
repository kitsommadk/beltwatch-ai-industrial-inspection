# Automatic belt edge-span baseline

## Purpose

Remove the caller-supplied `measured_span_px` shortcut from the image-processing path while keeping a simple, deterministic baseline that can be tested with generated fixtures and replay data.

## Current algorithm

`DarkScanlineEstimator` samples one configurable horizontal image row, converts each pixel to a scalar intensity, finds contiguous pixels darker than a configured threshold, and selects the longest qualifying run as the belt span.

The returned interval is half-open: `[left_x, right_x_exclusive)`. Therefore `span_px = right_x_exclusive - left_x` without an off-by-one ambiguity.

## What this validates

- image payload reaches the measurement pipeline
- edge geometry can be calculated without caller-supplied pixel width
- frame provenance survives through dimensional evidence
- calibration converts automatically estimated span to physical width
- deterministic PASS/WARNING/FAIL behavior can be exercised with generated fixtures
- the estimator is replaceable through the `SpanEstimator` protocol

## What this does not validate

This is not production metrology. It does not prove robustness to real belt texture, lighting gradients, shadows, glare, motion blur, perspective, lens distortion, debris, background clutter, damaged edges, or camera vibration.

## Why start simple

A deterministic baseline gives BeltWatch a reference implementation and repeatable expected values. More advanced algorithms can then be compared against a known baseline rather than replacing an undefined heuristic.

## Next algorithm gates

1. Generate a broader fixture matrix: shifted belts, width changes, brightness changes, edge defects, noise, partial occlusion.
2. Measure estimator error against fixture ground truth.
3. Add multi-row aggregation so one damaged/noisy scanline cannot dominate the width estimate.
4. Benchmark OpenCV thresholding/morphology/contour or gradient approaches on the same fixtures.
5. Add perspective/lens-correction before claiming physical width accuracy away from the calibrated image plane.
6. Replace generated fixtures with sanitized replay images when available.

The deterministic estimator remains a development/reference provider even after more advanced vision providers are added.