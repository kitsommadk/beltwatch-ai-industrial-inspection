# Frame exposure quality gate

BeltWatch now evaluates basic frame-level image quality before automatic belt geometry is allowed to proceed to dimensional classification.

The first frame-quality policy is intentionally deterministic and hardware-independent. It samples image intensity values and records:

- sampled pixel count
- mean intensity
- 5th-percentile intensity
- 95th-percentile intensity
- robust dynamic range (`p95 - p05`)
- low-clipped pixel fraction
- high-clipped pixel fraction

Automatic inspection fails closed when the frame does not satisfy the configured high-confidence policy. A degraded or invalid frame therefore cannot silently continue through edge estimation and become a dimensional PASS.

Replay policy `replay-frame-quality-v1` currently uses generated-fixture software gates:

- high-confidence minimum dynamic range: 80 intensity units
- valid minimum dynamic range: 30 intensity units
- high-confidence maximum clipped fraction: 1% per side
- valid maximum clipped fraction: 10% per side

The measurements and policy result are persisted in `inspection_frame_quality`, linked one-to-one with dimensional evidence. Evidence schema version 7 introduces this table while preserving the additive migration chain from earlier evidence schemas.

## Validation boundary

These thresholds are software/replay regression values only. They are **not** camera exposure settings, lighting requirements, gain limits, plant acceptance criteria, or physical metrology tolerances.

A real pilot policy must be derived from the actual camera/lens, lighting geometry, belt materials, speed, contamination, shadows, exposure, gain, and measured repeatability. The current gate establishes the architecture and fail-closed behavior needed to perform that later validation without pretending hardware-free fixtures are production evidence.
