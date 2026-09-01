"""Model and evaluation-record contracts for BeltWatch AI.

This module tracks what a model is, what hardware/runtime it targets, and what
measured evidence supports its current disposition. It does not load model weights
or imply production qualification.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class ModelDisposition(str, Enum):
    REJECTED = "rejected"
    EXPERIMENTAL = "experimental"
    PILOT_CANDIDATE = "pilot-candidate"


class ModelTask(str, Enum):
    ANOMALY = "anomaly"
    DETECTION = "detection"
    SEGMENTATION = "segmentation"


@dataclass(frozen=True)
class ModelIdentity:
    model_id: str
    version: str
    task: ModelTask
    framework: str
    artifact_ref: str
    dataset_manifest_id: str
    runtime_target: str
    hardware_target: str
    notes: str = ""

    def __post_init__(self) -> None:
        for name, value in (
            ("model_id", self.model_id),
            ("version", self.version),
            ("framework", self.framework),
            ("artifact_ref", self.artifact_ref),
            ("dataset_manifest_id", self.dataset_manifest_id),
            ("runtime_target", self.runtime_target),
            ("hardware_target", self.hardware_target),
        ):
            if not value.strip():
                raise ValueError(f"{name} must not be empty")


@dataclass(frozen=True)
class EvaluationMetrics:
    evaluated_at: datetime
    dataset_split: str
    cases: int
    misses: int
    false_alarms: int
    mean_latency_ms: float
    throughput_fps: float
    precision: float | None = None
    recall: float | None = None
    false_alarms_per_1000_ft: float | None = None
    peak_memory_mb: float | None = None
    notes: str = ""

    def __post_init__(self) -> None:
        if self.cases <= 0:
            raise ValueError("cases must be greater than zero")
        if self.misses < 0 or self.false_alarms < 0:
            raise ValueError("misses and false_alarms must not be negative")
        if self.mean_latency_ms < 0 or self.throughput_fps < 0:
            raise ValueError("latency and throughput must not be negative")
        for name, value in (("precision", self.precision), ("recall", self.recall)):
            if value is not None and not 0 <= value <= 1:
                raise ValueError(f"{name} must be between 0 and 1")
        if self.false_alarms_per_1000_ft is not None and self.false_alarms_per_1000_ft < 0:
            raise ValueError("false_alarms_per_1000_ft must not be negative")
        if self.peak_memory_mb is not None and self.peak_memory_mb < 0:
            raise ValueError("peak_memory_mb must not be negative")


@dataclass(frozen=True)
class ModelEvaluationRecord:
    identity: ModelIdentity
    metrics: EvaluationMetrics
    disposition: ModelDisposition
    evaluator_version: str
    reasons: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.evaluator_version.strip():
            raise ValueError("evaluator_version must not be empty")
        if self.disposition in {ModelDisposition.REJECTED, ModelDisposition.PILOT_CANDIDATE} and not self.reasons:
            raise ValueError("rejected and pilot-candidate records require explicit reasons")


class ModelRegistry:
    """In-memory registry keyed by immutable model/version pairs.

    Persistence can be added later; this contract makes duplicate versions and
    silent replacement invalid now.
    """

    def __init__(self) -> None:
        self._records: dict[tuple[str, str], ModelEvaluationRecord] = {}

    def register(self, record: ModelEvaluationRecord) -> None:
        key = (record.identity.model_id, record.identity.version)
        if key in self._records:
            raise ValueError(
                f"model evaluation already registered for {record.identity.model_id}:{record.identity.version}"
            )
        self._records[key] = record

    def get(self, model_id: str, version: str) -> ModelEvaluationRecord:
        key = (model_id, version)
        try:
            return self._records[key]
        except KeyError as exc:
            raise KeyError(f"unknown model evaluation {model_id}:{version}") from exc

    def all(self) -> tuple[ModelEvaluationRecord, ...]:
        return tuple(self._records[key] for key in sorted(self._records))

    def pilot_candidates(self) -> tuple[ModelEvaluationRecord, ...]:
        return tuple(
            record for record in self.all()
            if record.disposition == ModelDisposition.PILOT_CANDIDATE
        )
