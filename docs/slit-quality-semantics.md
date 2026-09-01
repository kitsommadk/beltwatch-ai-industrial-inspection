# Slit-run geometry quality semantics

BeltWatch's deterministic `slit-two-lane` estimator samples multiple image rows and requires exactly two belt-like spans on every sampled row.

For each lane, the reported geometry is an aggregate: median left/right edges plus observed edge/span spread. Edge contrast and edge sharpness are deliberately different: `min_edge_contrast` and `min_edge_sharpness` represent the weakest measurable value across the actual observed edges on all sampled rows.

If an edge-quality helper cannot measure a required sampled-row value, the aggregate metric remains unknown (`None`) rather than being converted to zero. This preserves the distinction between **not measured** and **measured poor quality**.

These metrics are deterministic software quality signals, not production metrology confidence. Their thresholds require qualification with the physical camera, lighting, belt materials, machine vibration and operating speed.
