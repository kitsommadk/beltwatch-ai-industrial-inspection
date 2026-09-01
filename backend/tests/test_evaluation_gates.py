from datetime import datetime, timezone

import pytest

from app.evaluation_gates import EvaluationGatePolicy, GateOutcome, evaluate_metrics
from app.model_registry import EvaluationMetrics


def metrics(**overrides):
    values = dict(
        evaluated_at=datetime.now(timezone.utc),
        dataset_split="holdout",
        cases=100,
        misses=0,
        false_alarms=2,
        mean_latency_ms=22.0,
        throughput_fps=35.0,
        precision=0.97,
        recall=0.99,
        false_alarms_per_1000_ft=1.5,
        peak_memory_mb=320.0,
    )
    values.update(overrides)
    return EvaluationMetrics(**values)


def policy(**overrides):
    values = dict(
        policy_id="pilot-candidate-v1",
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
    values.update(overrides)
    return EvaluationGatePolicy(**values)


def test_metrics_pass_when_every_required_gate_is_met():
    result = evaluate_metrics(metrics(), policy())
    assert result.outcome == GateOutcome.PASS
    assert result.passed is True
    assert result.failure_reasons == ()


def test_single_critical_miss_fails_zero_miss_policy():
    result = evaluate_metrics(metrics(misses=1), policy())
    assert result.outcome == GateOutcome.FAIL
    assert any(reason.startswith("misses:") for reason in result.failure_reasons)


def test_missing_required_optional_metric_fails_closed():
    result = evaluate_metrics(metrics(false_alarms_per_1000_ft=None), policy())
    assert result.outcome == GateOutcome.FAIL
    assert any("false_alarms_per_1000_ft" in reason for reason in result.failure_reasons)


def test_wrong_dataset_split_cannot_qualify_against_holdout_policy():
    result = evaluate_metrics(metrics(dataset_split="validation"), policy())
    assert result.outcome == GateOutcome.FAIL
    assert any(reason.startswith("dataset_split:") for reason in result.failure_reasons)


def test_each_failed_metric_is_reported_for_auditability():
    result = evaluate_metrics(
        metrics(misses=2, false_alarms=8, mean_latency_ms=60, throughput_fps=12),
        policy(),
    )
    failed = {check.metric for check in result.checks if not check.passed}
    assert {"misses", "false_alarms", "mean_latency_ms", "throughput_fps"} <= failed


def test_policy_validation_rejects_impossible_precision_requirement():
    with pytest.raises(ValueError, match="min_precision"):
        policy(min_precision=1.2)


def test_policy_without_optional_accuracy_metrics_only_checks_configured_fields():
    lightweight = policy(
        min_precision=None,
        min_recall=None,
        max_false_alarms_per_1000_ft=None,
        max_peak_memory_mb=None,
        required_dataset_split=None,
    )
    sparse = metrics(
        precision=None,
        recall=None,
        false_alarms_per_1000_ft=None,
        peak_memory_mb=None,
        dataset_split="test",
    )
    result = evaluate_metrics(sparse, lightweight)
    assert result.passed is True
