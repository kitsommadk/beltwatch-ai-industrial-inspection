# BeltWatch Span Benchmark Matrix

## Purpose

Measure deterministic belt-edge geometry accuracy before comparing heavier computer-vision models. This benchmark uses generated/replay fixtures with known ground truth. It does **not** validate physical camera calibration or production metrology.

## Baselines

1. `DarkScanlineEstimator` — one horizontal row; retained as the simplest reference.
2. `MultiRowDarkEstimator` — several horizontal rows; median edge aggregation plus cross-row geometry spread.

## Core metrics

- success rate: fraction of fixtures where an estimator returns a valid span
- exact match rate: fraction where both left and right edges exactly equal ground truth
- mean absolute span error (px): average absolute width error in pixels
- maximum absolute span error (px): worst width error in pixels
- mean edge error (px): average of left-edge and right-edge absolute error
- mean latency (ms): average estimator execution time in milliseconds
- cross-row span spread (px): difference between narrowest and widest valid row estimate

## Generated fixture matrix

Vary each factor independently first, then in combinations:

| Factor | Initial levels | Why it matters |
| --- | --- | --- |
| Belt width | 900, 940, 958, 960, 962, 1000 px | Dimensional sensitivity |
| Horizontal shift | -80 to +80 px | Belt tracking / lateral movement |
| Belt intensity | 20, 40, 70, 95 | Surface brightness |
| Background intensity | 130, 180, 220, 250 | Contrast margin |
| Sparse bright noise on belt | 0–5% pixels | Texture/specular artifacts |
| Sparse dark noise off belt | 0–5% pixels | Background contamination |
| Missing/corrupted scanlines | 0–40% sampled rows | Robustness to local occlusion |
| Edge taper | 0–20 px row-to-row shift | Nonparallel or damaged edges |

## Promotion gates for the deterministic estimator

These are engineering targets for generated/replay fixtures, not production acceptance limits:

- 100% success on clean fixtures
- 100% exact geometry on clean fixtures
- no silent output when fewer than the minimum valid rows are available
- reject fixtures whose cross-row span spread exceeds the configured consistency threshold
- benchmark failures remain visible in reported metrics rather than being discarded

## Next comparison

After the generated matrix is stable, compare the deterministic baseline with an OpenCV-based contour/segmentation estimator on the same fixtures and replay images. The provider contract stays unchanged so BeltWatch can select the best estimator from measured results instead of architecture preference.
