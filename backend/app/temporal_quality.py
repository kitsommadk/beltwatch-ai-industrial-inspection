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
    INCOMPARABLE = "incomparable"
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
    high_confidence_max_change_per_ft: float = 0.10
    valid_max_change_per_ft: float = 0.25
    max_comparable_position_gap_ft: float = 25.0

    def __post_init__(self) -> None:
        if not self.policy_id.strip():
            raise ValueError("policy_id must not be empty")
        if self.history_size < 1:
            raise ValueError("history_size must be at least one")
        if self.high_confidence_max_step_in < 0 or self.valid_max_step_in < self.high_confidence_max_step_in:
            raise ValueError("step thresholds are invalid")
        if self.high_confidence_max_median_deviation_in < 0 or self.valid_max_median_deviation_in < self.high_confidence_max_median_deviation_in:
            raise ValueError("median-deviation thresholds are invalid")
        if self.high_confidence_max_change_per_ft < 0 or self.valid_max_change_per_ft < self.high_confidence_max_change_per_ft:
            raise ValueError("position-rate thresholds are invalid")
        if self.max_comparable_position_gap_ft <= 0:
            raise ValueError("max_comparable_position_gap_ft must be positive")


@dataclass(frozen=True)
class TemporalQualityResult:
    policy_id: str
    status: TemporalQualityStatus
    history_count: int
    previous_width_in: float | None
    history_median_width_in: float | None
    step_change_in: float | None
    median_deviation_in: float | None
    previous_position_ft: float | None = None
    position_delta_ft: float | None = None
    width_change_per_ft: float | None = None
    reasons: tuple[str, ...] = field(default_factory=tuple)


class TemporalQualityError(ValueError):
    def __init__(self, result: TemporalQualityResult) -> None:
        self.result = result
        detail = "; ".join(result.reasons) or "measurement did not satisfy temporal quality policy"
        super().__init__(f"temporal quality {result.status.value}: {detail}")


def assess_temporal_width(current_width_in: float, history_widths_in: tuple[float, ...] | list[float], policy: TemporalQualityPolicy, *, current_position_ft: float | None = None, history_positions_ft: tuple[float, ...] | list[float] | None = None) -> TemporalQualityResult:
    history = tuple(float(value) for value in history_widths_in[-policy.history_size:])
    if not history:
        return TemporalQualityResult(policy.policy_id, TemporalQualityStatus.INSUFFICIENT_HISTORY, 0, None, None, None, None, reasons=("no comparable prior trusted measurements; temporal status is not yet established",))

    previous = history[-1]
    baseline = float(median(history))
    step = abs(float(current_width_in) - previous)
    median_deviation = abs(float(current_width_in) - baseline)
    previous_position = None
    position_delta = None
    change_per_ft = None

    if current_position_ft is not None or history_positions_ft is not None:
        if current_position_ft is None or not history_positions_ft:
            return TemporalQualityResult(policy.policy_id, TemporalQualityStatus.INCOMPARABLE, len(history), previous, baseline, step, median_deviation, reasons=("position history is incomplete; position-aware temporal comparison is unavailable",))
        positions = tuple(float(value) for value in history_positions_ft[-policy.history_size:])
        if len(positions) != len(history):
            return TemporalQualityResult(policy.policy_id, TemporalQualityStatus.INCOMPARABLE, len(history), previous, baseline, step, median_deviation, reasons=("width and position history lengths do not match",))
        previous_position = positions[-1]
        position_delta = float(current_position_ft) - previous_position
        if position_delta <= 0:
            return TemporalQualityResult(policy.policy_id, TemporalQualityStatus.INCOMPARABLE, len(history), previous, baseline, step, median_deviation, previous_position, position_delta, None, ("belt position did not advance; temporal width rate is not comparable",))
        if position_delta > policy.max_comparable_position_gap_ft:
            return TemporalQualityResult(policy.policy_id, TemporalQualityStatus.INCOMPARABLE, len(history), previous, baseline, step, median_deviation, previous_position, position_delta, None, (f"position gap {position_delta:.4f} ft exceeds comparable maximum {policy.max_comparable_position_gap_ft:.4f} ft",))
        change_per_ft = step / position_delta

    invalid: list[str] = []
    if step > policy.valid_max_step_in:
        invalid.append(f"step_change_in={step:.4f} exceeds valid maximum {policy.valid_max_step_in:.4f}")
    if median_deviation > policy.valid_max_median_deviation_in:
        invalid.append(f"median_deviation_in={median_deviation:.4f} exceeds valid maximum {policy.valid_max_median_deviation_in:.4f}")
    if change_per_ft is not None and change_per_ft > policy.valid_max_change_per_ft:
        invalid.append(f"width_change_per_ft={change_per_ft:.4f} exceeds valid maximum {policy.valid_max_change_per_ft:.4f}")
    if invalid:
        return TemporalQualityResult(policy.policy_id, TemporalQualityStatus.INVALID, len(history), previous, baseline, step, median_deviation, previous_position, position_delta, change_per_ft, tuple(invalid))

    degraded: list[str] = []
    if step > policy.high_confidence_max_step_in:
        degraded.append(f"step_change_in={step:.4f} exceeds high-confidence maximum {policy.high_confidence_max_step_in:.4f}")
    if median_deviation > policy.high_confidence_max_median_deviation_in:
        degraded.append(f"median_deviation_in={median_deviation:.4f} exceeds high-confidence maximum {policy.high_confidence_max_median_deviation_in:.4f}")
    if change_per_ft is not None and change_per_ft > policy.high_confidence_max_change_per_ft:
        degraded.append(f"width_change_per_ft={change_per_ft:.4f} exceeds high-confidence maximum {policy.high_confidence_max_change_per_ft:.4f}")
    if degraded:
        return TemporalQualityResult(policy.policy_id, TemporalQualityStatus.DEGRADED, len(history), previous, baseline, step, median_deviation, previous_position, position_delta, change_per_ft, tuple(degraded))

    return TemporalQualityResult(policy.policy_id, TemporalQualityStatus.HIGH_CONFIDENCE, len(history), previous, baseline, step, median_deviation, previous_position, position_delta, change_per_ft, ("measurement is consistent with recent comparable trusted width history",))
