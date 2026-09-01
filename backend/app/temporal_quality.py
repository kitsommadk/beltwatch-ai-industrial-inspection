"""Deterministic temporal consistency checks for sequential belt-width evidence.

These checks are hardware-independent software validation gates. Thresholds must be
qualified against physical belt speed, camera cadence, vibration, and metrology data
before production use.
"""

from dataclasses import dataclass, field
from enum import Enum
from statistics import median


class TemporalQualityStatus(str, Enum):
    INSUFFICIENT_HISTORY = "insufficient-history"
    HIGH_CONFIDENCE = "high-confidence"
    DEGRADED = "degraded"
    INVALID = "invalid"


@dataclass(frozen=True)
class TemporalQualityPolicy:
    policy_id: str
    history_size: int = 5
    high_confidence_max_step_in: float = 0.10
    valid_max_step_in: float = 0.25
    high_confidence_max_median_deviation_in: float = 0.10
    valid_max_median_deviation_in: float = 0.25

    def __post_init__(self) -> None:
        if not self.policy_id.strip():
            raise ValueError("policy_id must not be empty")
        if self.history_size < 1:
            raise ValueError("history_size must be at least one")
        if self.high_confidence_max_step_in < 0 or self.valid_max_step_in < self.high_confidence_max_step_in:
            raise ValueError("step thresholds are invalid")
        if self.high_confidence_max_median_deviation_in < 0 or self.valid_max_median_deviation_in < self.high_confidence_max_median_deviation_in:
            raise ValueError("median-deviation thresholds are invalid")


@dataclass(frozen=True)
class TemporalQualityResult:
    policy_id: str
    status: TemporalQualityStatus
    history_count: int
    previous_width_in: float | None
    history_median_width_in: float | None
    step_change_in: float | None
    median_deviation_in: float | None
    reasons: tuple[str, ...] = field(default_factory=tuple)


class TemporalQualityError(ValueError):
    def __init__(self, result: TemporalQualityResult) -> None:
        self.result = result
        detail = "; ".join(result.reasons) or "measurement did not satisfy temporal quality policy"
        super().__init__(f"temporal quality {result.status.value}: {detail}")


def assess_temporal_width(current_width_in: float, history_widths_in: tuple[float, ...] | list[float], policy: TemporalQualityPolicy) -> TemporalQualityResult:
    history = tuple(float(value) for value in history_widths_in[-policy.history_size:])
    if not history:
        return TemporalQualityResult(
            policy.policy_id,
            TemporalQualityStatus.INSUFFICIENT_HISTORY,
            0,
            None,
            None,
            None,
            None,
            ("no comparable prior trusted measurements; temporal status is not yet established",),
        )

    previous = history[-1]
    baseline = float(median(history))
    step = abs(float(current_width_in) - previous)
    median_deviation = abs(float(current_width_in) - baseline)

    invalid: list[str] = []
    if step > policy.valid_max_step_in:
        invalid.append(f"step_change_in={step:.4f} exceeds valid maximum {policy.valid_max_step_in:.4f}")
    if median_deviation > policy.valid_max_median_deviation_in:
        invalid.append(f"median_deviation_in={median_deviation:.4f} exceeds valid maximum {policy.valid_max_median_deviation_in:.4f}")
    if invalid:
        return TemporalQualityResult(policy.policy_id, TemporalQualityStatus.INVALID, len(history), previous, baseline, step, median_deviation, tuple(invalid))

    degraded: list[str] = []
    if step > policy.high_confidence_max_step_in:
        degraded.append(f"step_change_in={step:.4f} exceeds high-confidence maximum {policy.high_confidence_max_step_in:.4f}")
    if median_deviation > policy.high_confidence_max_median_deviation_in:
        degraded.append(f"median_deviation_in={median_deviation:.4f} exceeds high-confidence maximum {policy.high_confidence_max_median_deviation_in:.4f}")
    if degraded:
        return TemporalQualityResult(policy.policy_id, TemporalQualityStatus.DEGRADED, len(history), previous, baseline, step, median_deviation, tuple(degraded))

    return TemporalQualityResult(policy.policy_id, TemporalQualityStatus.HIGH_CONFIDENCE, len(history), previous, baseline, step, median_deviation, ("measurement is consistent with recent comparable trusted width history",))
