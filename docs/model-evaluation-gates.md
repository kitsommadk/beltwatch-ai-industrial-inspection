# Model evaluation gates

BeltWatch now has a deterministic evaluation-gate layer between raw model metrics and any engineering promotion decision.

## Purpose

`backend/app/evaluation_gates.py` compares an `EvaluationMetrics` record against an explicit `EvaluationGatePolicy`. The result contains one check per configured requirement, an overall pass/fail outcome, and machine-readable failure reasons.

The goal is to make model qualification reproducible. A candidate should not become a `pilot-candidate` because it looked promising in one demo or because a model family is popular.

## Supported gates

A policy can constrain:

- maximum misses;
- maximum false alarms;
- maximum mean inference latency;
- minimum throughput in frames per second (FPS);
- minimum precision;
- minimum recall;
- maximum false alarms per 1,000 feet;
- maximum peak memory use;
- required evaluation split such as a frozen holdout set.

Only configured optional metrics are required. When a policy requires an optional metric and that metric is absent, the gate fails closed rather than assuming a pass.

## Example only

A development policy might require zero misses on a particular frozen holdout set, a minimum recall, bounded false alarms, and an edge-device latency/resource budget. Those numbers must be chosen from the real inspection risk, belt speed, camera rate, operator burden, edge hardware, and representative dataset. Values used in unit tests are software-test fixtures, not production acceptance criteria.

## Promotion boundary

Passing a model-evaluation gate means only that the supplied metrics satisfied the named software policy. It does **not** prove:

- physical camera performance;
- optics, exposure, lighting, or motion-blur robustness;
- calibration accuracy;
- USB or edge-computer stability;
- representative plant performance;
- production qualification.

A future promotion service may use a passing `GateResult` as one required input when creating a `pilot-candidate` record. Physical pilot validation remains a later independent gate.

## Why fail closed

Missing required measurements are evidence gaps. BeltWatch should report them explicitly rather than manufacture confidence. This principle also applies to unknown providers, stale cameras, invalid calibration, and ambiguous geometry elsewhere in the system.
