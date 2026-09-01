"""Deterministic qualification gates for BeltWatch model evaluations.

A gate compares measured EvaluationMetrics against an explicit policy and returns
machine-readable pass/fail reasons. Passing a development gate is not physical-camera
or production qualification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum

from .model_registry import EvaluationMetrics


class GateOutcome(str, Enum):
    PASS = "pass"
    FAIL = "fail"


@dataclass(frozen=True)
class EvaluationGatePolicy:
    policy_id: str
    max_misses: int
    max_false_alarms: int
    max_mean_latency_ms: float
    min_throughput_fps: float
    min_precision: float | None = None
    min_recall: float | None = None
    max_false_alarms_per_1000_ft: float | None = None
    max_peak_memory_mb: float | None = None
    required_dataset_split: str | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        if not self.policy_id.strip():
            raise ValueError("policy_id must not be empty")
        if self.max_misses < 0 or self.max_false_alarms < 0:
            raise ValueError("miss and false-alarm limits must not be negative")
        if self.max_mean_latency_ms < 0 or self.min_throughput_fps < 0:
            raise ValueError("latency and throughput limits must not be negative")
        for name, value in (("min_precision", self.min_precision), ("min_recall", self.min_recall)):
            if value is not None and not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        if self.max_false_alarms_per_1000_ft is not None and self.max_false_alarms_per_1000_ft < 0:
            raise ValueError("max_false_alarms_per_1000_ft must not be negative")
        if self.max_peak_memory_mb is not None and self.max_peak_memory_mb < 0:
            raise ValueError("max_peak_memory_mb must not be negative")
        if self.required_dataset_split is not None and not self.required_dataset_split.strip():
            raise ValueError("required_dataset_split must not be blank")


@dataclass(frozen=True)
class GateCheck:
    metric: str
    passed: bool
    observed: float | int | str | None
    requirement: str


@dataclass(frozen=True)
class GateResult:
    policy_id: str
    outcome: GateOutcome
    checks: tuple[GateCheck, ...] = field(default_factory=tuple)

    @property
    def passed(self) -> bool:
        return self.outcome == GateOutcome.PASS

    @property
    def failure_reasons(self) -> tuple[str, ...]:
        return tuple(
            f"{check.metric}: observed {check.observed!r}; requires {check.requirement}"
            for check in self.checks
            if not check.passed
        )


def evaluate_metrics(metrics: EvaluationMetrics, policy: EvaluationGatePolicy) -> GateResult:
    """Evaluate metrics against policy using fail-closed optional-metric semantics.

    If a policy requires precision, recall, footage-normalized false alarms, or peak
    memory and that measurement is absent, the corresponding check fails.
    """
    checks: list[GateCheck] = []

    def add(metric: str, passed: bool, observed, requirement: str) -> None:
        checks.append(GateCheck(metric, passed, observed, requirement))

    add("misses", metrics.misses <= policy.max_misses, metrics.misses, f"<= {policy.max_misses}")
    add(
        "false_alarms",
        metrics.false_alarms <= policy.max_false_alarms,
        metrics.false_alarms,
        f"<= {policy.max_false_alarms}",
    )
    add(
        "mean_latency_ms",
        metrics.mean_latency_ms <= policy.max_mean_latency_ms,
        metrics.mean_latency_ms,
        f"<= {policy.max_mean_latency_ms}",
    )
    add(
        "throughput_fps",
        metrics.throughput_fps >= policy.min_throughput_fps,
        metrics.throughput_fps,
        f">= {policy.min_throughput_fps}",
    )

    if policy.required_dataset_split is not None:
        add(
            "dataset_split",
            metrics.dataset_split == policy.required_dataset_split,
            metrics.dataset_split,
            f"== {policy.required_dataset_split!r}",
        )

    if policy.min_precision is not None:
        add(
            "precision",
            metrics.precision is not None and metrics.precision >= policy.min_precision,
            metrics.precision,
            f">= {policy.min_precision}",
        )

    if policy.min_recall is not None:
        add(
            "recall",
            metrics.recall is not None and metrics.recall >= policy.min_recall,
            metrics.recall,
            f">= {policy.min_recall}",
        )

    if policy.max_false_alarms_per_1000_ft is not None:
        add(
            "false_alarms_per_1000_ft",
            metrics.false_alarms_per_1000_ft is not None
            and metrics.false_alarms_per_1000_ft <= policy.max_false_alarms_per_1000_ft,
            metrics.false_alarms_per_1000_ft,
            f"<= {policy.max_false_alarms_per_1000_ft}",
        )

    if policy.max_peak_memory_mb is not None:
        add(
            "peak_memory_mb",
            metrics.peak_memory_mb is not None and metrics.peak_memory_mb <= policy.max_peak_memory_mb,
            metrics.peak_memory_mb,
            f"<= {policy.max_peak_memory_mb}",
        )

    outcome = GateOutcome.PASS if all(check.passed for check in checks) else GateOutcome.FAIL
    return GateResult(policy.policy_id, outcome, tuple(checks))
