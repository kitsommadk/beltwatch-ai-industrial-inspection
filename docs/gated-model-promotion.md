# Gate-backed model promotion

BeltWatch now has a narrow promotion service between model evaluation gates and the model registry.

## Why this boundary exists

A model should not become a `pilot-candidate` merely because someone manually labels it that way after looking at promising metrics. `backend/app/model_promotion.py` recomputes the named evaluation policy against the exact `EvaluationMetrics` object being considered for promotion.

If the gate fails, the promotion decision contains the gate failure reasons and no `ModelEvaluationRecord` is created for pilot candidacy.

If the gate passes, the service may create a `pilot-candidate` record that includes the gate policy identifier in its reasons. The record can then be registered through the existing `ModelRegistry`.

## Trust boundary

The service accepts `ModelIdentity`, `EvaluationMetrics`, and an `EvaluationGatePolicy`, then calls the deterministic gate engine internally. A caller does not supply a previously computed `GateResult`, because that result could have been generated from a different metrics record.

This keeps the decision path tied to the exact metrics being promoted:

`ModelIdentity + EvaluationMetrics + EvaluationGatePolicy -> evaluate gate -> PromotionDecision -> optional pilot-candidate record`

## Fail-closed behavior

No pilot-candidate record is produced when:

- a required metric misses its threshold;
- a required optional metric is absent;
- the dataset split is wrong;
- latency, throughput, memory, miss, or false-alarm constraints fail.

Failure reasons remain available on the `PromotionDecision` for audit and engineering review.

## What this does not prove

A `pilot-candidate` remains only a software-qualified candidate. It does not prove physical-camera performance, calibration accuracy, lighting robustness, motion-blur robustness, USB stability, real edge-computer throughput, plant representativeness, or production fitness.

Physical pilot validation remains a separate later gate.
