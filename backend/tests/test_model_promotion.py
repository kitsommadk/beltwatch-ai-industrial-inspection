from datetime import datetime, timezone

from app.evaluation_gates import EvaluationGatePolicy
from app.model_promotion import evaluate_for_pilot
from app.model_registry import (
    EvaluationMetrics,
    ModelDisposition,
    ModelIdentity,
    ModelRegistry,
    ModelTask,
)


def identity() -> ModelIdentity:
    return ModelIdentity(
        model_id="belt-anomaly-baseline",
        version="1.0.0",
        task=ModelTask.ANOMALY,
        framework="pytorch",
        artifact_ref="private://models/belt-anomaly-baseline/1.0.0",
        dataset_manifest_id="manifest-v1",
        runtime_target="onnx-runtime",
        hardware_target="edge-cpu",
    )


def metrics(**overrides) -> EvaluationMetrics:
    values = dict(
        evaluated_at=datetime.now(timezone.utc),
        dataset_split="holdout",
        cases=200,
        misses=0,
        false_alarms=2,
        mean_latency_ms=24.0,
        throughput_fps=34.0,
        precision=0.97,
        recall=0.99,
        false_alarms_per_1000_ft=1.2,
        peak_memory_mb=310.0,
    )
    values.update(overrides)
    return EvaluationMetrics(**values)


def policy() -> EvaluationGatePolicy:
    return EvaluationGatePolicy(
        policy_id="pilot-candidate-development-v1",
        max_misses=0,
        max_false_alarms=3,
        max_mean_latency_ms=30.0,
        min_throughput_fps=30.0,
        min_precision=0.95,
        min_recall=0.98,
        max_false_alarms_per_1000_ft=2.0,
        max_peak_memory_mb=512.0,
        required_dataset_split="holdout",
    )


def test_passing_gate_creates_pilot_candidate_record():
    decision = evaluate_for_pilot(
        identity=identity(),
        metrics=metrics(),
        policy=policy(),
        evaluator_version="promotion-service-v1",
    )

    assert decision.eligible is True
    assert decision.gate_result.passed is True
    assert decision.record is not None
    assert decision.record.disposition == ModelDisposition.PILOT_CANDIDATE
    assert "pilot-candidate-development-v1" in decision.record.reasons[0]


def test_failed_gate_cannot_create_pilot_candidate_record():
    decision = evaluate_for_pilot(
        identity=identity(),
        metrics=metrics(misses=1),
        policy=policy(),
        evaluator_version="promotion-service-v1",
    )

    assert decision.eligible is False
    assert decision.record is None
    assert any(reason.startswith("misses:") for reason in decision.failure_reasons)


def test_missing_required_metric_cannot_create_candidate_record():
    decision = evaluate_for_pilot(
        identity=identity(),
        metrics=metrics(recall=None),
        policy=policy(),
        evaluator_version="promotion-service-v1",
    )

    assert decision.eligible is False
    assert decision.record is None
    assert any(reason.startswith("recall:") for reason in decision.failure_reasons)


def test_successful_candidate_can_be_registered_normally():
    decision = evaluate_for_pilot(
        identity=identity(),
        metrics=metrics(),
        policy=policy(),
        evaluator_version="promotion-service-v1",
        supplemental_reasons=("frozen holdout evaluation completed",),
    )
    registry = ModelRegistry()

    assert decision.record is not None
    registry.register(decision.record)

    stored = registry.get("belt-anomaly-baseline", "1.0.0")
    assert stored.disposition == ModelDisposition.PILOT_CANDIDATE
    assert "frozen holdout evaluation completed" in stored.reasons


def test_gate_is_recomputed_from_the_metrics_being_promoted():
    passing = metrics()
    failing = metrics(throughput_fps=10.0)

    first = evaluate_for_pilot(
        identity=identity(),
        metrics=passing,
        policy=policy(),
        evaluator_version="promotion-service-v1",
    )
    second = evaluate_for_pilot(
        identity=identity(),
        metrics=failing,
        policy=policy(),
        evaluator_version="promotion-service-v1",
    )

    assert first.eligible is True
    assert second.eligible is False
    assert second.record is None
