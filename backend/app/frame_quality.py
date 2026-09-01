"""Hardware-independent frame quality checks for automatic inspection evidence."""

from dataclasses import dataclass, field
from enum import Enum
from numbers import Number
from statistics import mean
from typing import Any


class FrameQualityStatus(str, Enum):
    HIGH_CONFIDENCE = "high-confidence"
    DEGRADED = "degraded"
    INVALID = "invalid"


@dataclass(frozen=True)
class FrameQualityPolicy:
    policy_id: str
    high_confidence_min_dynamic_range: float = 80.0
    valid_min_dynamic_range: float = 30.0
    high_confidence_max_clipped_fraction: float = 0.01
    valid_max_clipped_fraction: float = 0.10
    low_clip_level: float = 2.0
    high_clip_level: float = 253.0
    max_samples: int = 4096

    def __post_init__(self) -> None:
        if not self.policy_id.strip():
            raise ValueError("policy_id must not be empty")
        if self.valid_min_dynamic_range < 0 or self.high_confidence_min_dynamic_range < self.valid_min_dynamic_range:
            raise ValueError("dynamic range thresholds are invalid")
        if not 0 <= self.high_confidence_max_clipped_fraction <= self.valid_max_clipped_fraction <= 1:
            raise ValueError("clipped fraction thresholds must satisfy 0 <= high <= valid <= 1")
        if not 0 <= self.low_clip_level < self.high_clip_level <= 255:
            raise ValueError("clip levels must satisfy 0 <= low < high <= 255")
        if self.max_samples <= 0:
            raise ValueError("max_samples must be greater than zero")


@dataclass(frozen=True)
class FrameQualityMetrics:
    sampled_pixels: int
    mean_intensity: float
    p05_intensity: float
    p95_intensity: float
    dynamic_range: float
    low_clipped_fraction: float
    high_clipped_fraction: float


@dataclass(frozen=True)
class FrameQualityResult:
    policy_id: str
    status: FrameQualityStatus
    metrics: FrameQualityMetrics
    reasons: tuple[str, ...] = field(default_factory=tuple)


class FrameQualityError(ValueError):
    def __init__(self, result: FrameQualityResult) -> None:
        self.result = result
        detail = "; ".join(result.reasons) or "frame did not satisfy image-quality policy"
        super().__init__(f"frame quality {result.status.value}: {detail}")


def _intensity(pixel: Any) -> float:
    if isinstance(pixel, Number):
        return float(pixel)
    try:
        values = [float(value) for value in pixel]
    except TypeError as exc:
        raise ValueError("unsupported pixel format") from exc
    if not values:
        raise ValueError("pixel channel list must not be empty")
    return sum(values) / len(values)


def _flatten_sample(image: Any, max_samples: int) -> list[float]:
    shape = getattr(image, "shape", None)
    if shape is not None and len(shape) >= 2:
        height, width = int(shape[0]), int(shape[1])
    else:
        if not image or not image[0]:
            raise ValueError("image must not be empty")
        height, width = len(image), len(image[0])
    total = height * width
    stride = max(1, total // max_samples)
    values: list[float] = []
    index = 0
    for y in range(height):
        row = image[y]
        for x in range(width):
            if index % stride == 0:
                values.append(_intensity(row[x]))
                if len(values) >= max_samples:
                    return values
            index += 1
    return values


def _percentile(sorted_values: list[float], fraction: float) -> float:
    if not sorted_values:
        raise ValueError("cannot calculate percentile of empty sample")
    index = int(round((len(sorted_values) - 1) * fraction))
    return sorted_values[index]


def assess_frame_quality(image: Any, policy: FrameQualityPolicy) -> FrameQualityResult:
    values = _flatten_sample(image, policy.max_samples)
    ordered = sorted(values)
    p05 = _percentile(ordered, 0.05)
    p95 = _percentile(ordered, 0.95)
    low_fraction = sum(value <= policy.low_clip_level for value in values) / len(values)
    high_fraction = sum(value >= policy.high_clip_level for value in values) / len(values)
    metrics = FrameQualityMetrics(
        sampled_pixels=len(values),
        mean_intensity=float(mean(values)),
        p05_intensity=p05,
        p95_intensity=p95,
        dynamic_range=float(p95 - p05),
        low_clipped_fraction=low_fraction,
        high_clipped_fraction=high_fraction,
    )

    invalid: list[str] = []
    if metrics.dynamic_range < policy.valid_min_dynamic_range:
        invalid.append(f"dynamic_range={metrics.dynamic_range:.1f} below valid minimum {policy.valid_min_dynamic_range:.1f}")
    if metrics.low_clipped_fraction > policy.valid_max_clipped_fraction:
        invalid.append(f"low_clipped_fraction={metrics.low_clipped_fraction:.3f} exceeds valid maximum {policy.valid_max_clipped_fraction:.3f}")
    if metrics.high_clipped_fraction > policy.valid_max_clipped_fraction:
        invalid.append(f"high_clipped_fraction={metrics.high_clipped_fraction:.3f} exceeds valid maximum {policy.valid_max_clipped_fraction:.3f}")
    if invalid:
        return FrameQualityResult(policy.policy_id, FrameQualityStatus.INVALID, metrics, tuple(invalid))

    degraded: list[str] = []
    if metrics.dynamic_range < policy.high_confidence_min_dynamic_range:
        degraded.append(f"dynamic_range={metrics.dynamic_range:.1f} below high-confidence minimum {policy.high_confidence_min_dynamic_range:.1f}")
    if metrics.low_clipped_fraction > policy.high_confidence_max_clipped_fraction:
        degraded.append(f"low_clipped_fraction={metrics.low_clipped_fraction:.3f} exceeds high-confidence maximum {policy.high_confidence_max_clipped_fraction:.3f}")
    if metrics.high_clipped_fraction > policy.high_confidence_max_clipped_fraction:
        degraded.append(f"high_clipped_fraction={metrics.high_clipped_fraction:.3f} exceeds high-confidence maximum {policy.high_confidence_max_clipped_fraction:.3f}")
    if degraded:
        return FrameQualityResult(policy.policy_id, FrameQualityStatus.DEGRADED, metrics, tuple(degraded))

    return FrameQualityResult(policy.policy_id, FrameQualityStatus.HIGH_CONFIDENCE, metrics, ("frame satisfied all configured high-confidence gates",))
