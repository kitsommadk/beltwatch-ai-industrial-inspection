# OpenCV Span Benchmark

## Purpose

BeltWatch now has two classical image-geometry baselines behind the same `SpanEstimator` contract:

1. `MultiRowDarkEstimator` — pure-Python multi-row threshold scanning.
2. `OpenCVContourEstimator` — OpenCV thresholding + morphology + contour extraction.

The purpose is comparison, not premature selection. Both providers must be measured on the same generated/replay fixtures.

## What the OpenCV provider does

For each frame it:

1. converts color input to grayscale when needed,
2. thresholds dark pixels into a binary mask,
3. applies morphological closing to connect small gaps,
4. finds external contours,
5. rejects contours that are too small or too short,
6. selects the largest remaining contour,
7. returns the contour bounding interval as the belt pixel span.

This is classical computer vision, not a trained AI model.

## Benchmark metrics

Use the shared benchmark harness to compare:

- success rate,
- exact edge-match rate,
- mean absolute span error in pixels,
- maximum span error,
- mean left/right edge error,
- mean processing latency.

## Current validation boundary

Generated fixtures can validate deterministic geometry behavior, error accounting, provider interchangeability, and software performance. They cannot validate physical metrology, lens distortion, real illumination, belt texture, motion blur, vibration, perspective, contamination, or camera mounting.

## Promotion rule

No estimator becomes the BeltWatch pilot default because it is more sophisticated. Promotion requires better measured behavior on representative replay data and later physical-camera data, while maintaining acceptable latency and visible failure handling.
