"""Gate-backed promotion decisions for BeltWatch model candidates.

This module connects measured model evaluation metrics to the model registry without
allowing a failed software gate to produce a ``pilot-candidate`` record. Passing this
software gate still does not imply physical-camera or production qualification.
"""

from __future__ import annotations

from dataclasses import dataclass

from .evaluation_gates import EvaluationGatePolicy, GateResult, evaluate_metrics
from .model_registry import (
    EvaluationMetrics,
    ModelDisposition,
    ModelEvaluationRecord,
    ModelIdentity,
)


@dataclass(frozen=True)
class PromotionDecision:
    """Result of evaluating one model/version for pilot candidacy."""

    eligible: bool
    gate_result: GateResult
    record: ModelEvaluationRecord | None

    @property
    def failure_reasons(self) -> tuple[str, ...]:
        return self.gate_result.failure_reasons


def evaluate_for_pilot(
    *,
    identity: ModelIdentity,
    metrics: EvaluationMetrics,
    policy: EvaluationGatePolicy,
    evaluator_version: str,
    supplemental_reasons: tuple[str, ...] = (),
) -> PromotionDecision:
    """Evaluate one model and create a pilot-candidate record only on gate success.

    The gate is recomputed from the supplied metrics inside this function. Callers do
    not pass in a pre-computed ``GateResult`` that could have come from different
    metrics. A failing gate returns an ineligible decision and no registry record.
    """
    if not evaluator_version.strip():
        raise ValueError("evaluator_version must not be empty")

    gate_result = evaluate_metrics(metrics, policy)
    if not gate_result.passed:
        return PromotionDecision(False, gate_result, None)

    reasons = (
        f"passed evaluation gate {policy.policy_id!r}",
        *tuple(reason.strip() for reason in supplemental_reasons if reason.strip()),
    )
    record = ModelEvaluationRecord(
        identity=identity,
        metrics=metrics,
        disposition=ModelDisposition.PILOT_CANDIDATE,
        evaluator_version=evaluator_version,
        reasons=reasons,
    )
    return PromotionDecision(True, gate_result, record)
