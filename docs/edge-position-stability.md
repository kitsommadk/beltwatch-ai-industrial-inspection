# Edge-position stability

BeltWatch now tracks left-edge and right-edge movement independently across the scan rows used by the multi-row geometry estimator.

A stable total width is not enough to prove stable geometry. For example, every row can measure exactly 960 px wide while the whole detected belt shifts sideways across the image. In that case `span_spread_px` can remain zero even though both edges are moving.

The multi-row result therefore records:

- `span_spread_px`: range of measured widths across valid rows;
- `left_edge_spread_px`: range of left-edge positions across valid rows;
- `right_edge_spread_px`: range of right-edge positions across valid rows.

The geometry-quality gate checks all three signals. The replay policy `replay-multirow-quality-v2` currently treats more than 2 px of either edge spread as degraded and more than 12 px as invalid.

These thresholds are deterministic software-regression gates only. They are not physical metrology tolerances. Production limits must be established after camera mounting, lens/perspective calibration, lighting, belt motion, vibration, and representative plant imagery are validated.
