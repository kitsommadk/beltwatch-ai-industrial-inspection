from datetime import datetime, timezone

import pytest

from app.model_registry import (
    EvaluationMetrics,
    ModelDisposition,
    ModelEvaluationRecord,
    ModelIdentity,
    ModelRegistry,
    ModelTask,
)


def identity(version="1.0.0") -> ModelIdentity:
    return ModelIdentity(
        model_id="belt-anomaly-baseline",
        version=version,
        task=ModelTask.ANOMALY,
        framework="pytorch",
        artifact_ref="private://models/belt-anomaly-baseline/1.0.0",
        dataset_manifest_id="manifest-2026-09-a",
        runtime_target="onnx-runtime",
        hardware_target="geekom-air12-lite-cpu",
    )


def metrics(**overrides) -> EvaluationMetrics:
    values = dict(
        evaluated_at=datetime.now(timezone.utc),
        dataset_split="holdout",
        cases=100,
        misses=2,
        false_alarms=4,
        mean_latency_ms=18.5,
        throughput_fps=42.0,
        precision=0.94,
        recall=0.92,
        false_alarms_per_1000_ft=0.8,
        peak_memory_mb=640.0,
    )
    values.update(overrides)
    return EvaluationMetrics(**values)


def record(version="1.0.0", disposition=ModelDisposition.EXPERIMENTAL, reasons=()):
    return ModelEvaluationRecord(
        identity=identity(version),
        metrics=metrics(),
        disposition=disposition,
        evaluator_version="eval-v1",
        reasons=reasons,
    )


def test_registry_rejects_duplicate_model_version():
    registry = ModelRegistry()
    registry.register(record())
    with pytest.raises(ValueError, match="already registered"):
        registry.register(record())


def test_registry_keeps_versions_separate():
    registry = ModelRegistry()
    registry.register(record("1.0.0"))
    registry.register(record("1.1.0"))
    assert len(registry.all()) == 2
    assert registry.get("belt-anomaly-baseline", "1.1.0").identity.version == "1.1.0"


def test_pilot_candidate_requires_explicit_reasons():
    with pytest.raises(ValueError, match="explicit reasons"):
        record(disposition=ModelDisposition.PILOT_CANDIDATE)


def test_rejected_model_requires_explicit_reasons():
    with pytest.raises(ValueError, match="explicit reasons"):
        record(disposition=ModelDisposition.REJECTED)


def test_pilot_candidate_filter_is_explicit():
    registry = ModelRegistry()
    registry.register(record("1.0.0"))
    registry.register(
        record(
            "1.1.0",
            disposition=ModelDisposition.PILOT_CANDIDATE,
            reasons=("met frozen-holdout gate", "latency within CPU budget"),
        )
    )
    candidates = registry.pilot_candidates()
    assert len(candidates) == 1
    assert candidates[0].identity.version == "1.1.0"


def test_metrics_validate_probability_bounds():
    with pytest.raises(ValueError, match="precision"):
        metrics(precision=1.2)


def test_metrics_reject_negative_latency():
    with pytest.raises(ValueError, match="latency"):
        metrics(mean_latency_ms=-1)
