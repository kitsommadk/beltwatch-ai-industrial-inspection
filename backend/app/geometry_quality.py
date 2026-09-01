"""Deterministic quality gates for image-derived belt geometry."""

from dataclasses import dataclass, field
from enum import Enum

from .edge_span import BeltSpan


class GeometryQualityStatus(str, Enum):
    HIGH_CONFIDENCE = "high-confidence"
    DEGRADED = "degraded"
    INVALID = "invalid"


@dataclass(frozen=True)
class GeometryQualityPolicy:
    policy_id: str
    high_confidence_min_rows: int = 3
    valid_min_rows: int = 1
    high_confidence_max_span_spread_px: int = 2
    valid_max_span_spread_px: int = 12
    high_confidence_max_edge_spread_px: int = 2
    valid_max_edge_spread_px: int = 12
    high_confidence_min_edge_contrast: float = 0.0
    valid_min_edge_contrast: float = 0.0
    high_confidence_min_edge_sharpness: float = 0.0
    valid_min_edge_sharpness: float = 0.0

    def __post_init__(self) -> None:
        if not self.policy_id.strip():
            raise ValueError("policy_id must not be empty")
        if self.valid_min_rows <= 0:
            raise ValueError("valid_min_rows must be greater than zero")
        if self.high_confidence_min_rows < self.valid_min_rows:
            raise ValueError("high_confidence_min_rows must be >= valid_min_rows")
        for name, value in (
            ("high_confidence_max_span_spread_px", self.high_confidence_max_span_spread_px),
            ("valid_max_span_spread_px", self.valid_max_span_spread_px),
            ("high_confidence_max_edge_spread_px", self.high_confidence_max_edge_spread_px),
            ("valid_max_edge_spread_px", self.valid_max_edge_spread_px),
            ("high_confidence_min_edge_contrast", self.high_confidence_min_edge_contrast),
            ("valid_min_edge_contrast", self.valid_min_edge_contrast),
            ("high_confidence_min_edge_sharpness", self.high_confidence_min_edge_sharpness),
            ("valid_min_edge_sharpness", self.valid_min_edge_sharpness),
        ):
            if value < 0:
                raise ValueError(f"{name} must not be negative")
        if self.valid_max_span_spread_px < self.high_confidence_max_span_spread_px:
            raise ValueError("valid_max_span_spread_px must be >= high_confidence_max_span_spread_px")
        if self.valid_max_edge_spread_px < self.high_confidence_max_edge_spread_px:
            raise ValueError("valid_max_edge_spread_px must be >= high_confidence_max_edge_spread_px")
        if self.high_confidence_min_edge_contrast < self.valid_min_edge_contrast:
            raise ValueError("high_confidence_min_edge_contrast must be >= valid_min_edge_contrast")
        if self.high_confidence_min_edge_sharpness < self.valid_min_edge_sharpness:
            raise ValueError("high_confidence_min_edge_sharpness must be >= valid_min_edge_sharpness")


@dataclass(frozen=True)
class GeometryQualityResult:
    policy_id: str
    status: GeometryQualityStatus
    reasons: tuple[str, ...] = field(default_factory=tuple)

    @property
    def high_confidence(self) -> bool:
        return self.status == GeometryQualityStatus.HIGH_CONFIDENCE


class GeometryQualityError(ValueError):
    def __init__(self, result: GeometryQualityResult) -> None:
        self.result = result
        detail = "; ".join(result.reasons) or "geometry did not satisfy the quality gate"
        super().__init__(f"geometry quality {result.status.value}: {detail}")


DEFAULT_GEOMETRY_QUALITY_POLICY = GeometryQualityPolicy(
    policy_id="default-geometry-quality-v4",
    high_confidence_min_rows=1,
    valid_min_rows=1,
    high_confidence_max_span_spread_px=0,
    valid_max_span_spread_px=12,
    high_confidence_max_edge_spread_px=0,
    valid_max_edge_spread_px=12,
)


def assess_geometry(span: BeltSpan, policy: GeometryQualityPolicy) -> GeometryQualityResult:
    invalid_reasons: list[str] = []
    if span.sampled_rows < policy.valid_min_rows:
        invalid_reasons.append(f"sampled_rows={span.sampled_rows} below valid minimum {policy.valid_min_rows}")
    if span.span_spread_px > policy.valid_max_span_spread_px:
        invalid_reasons.append(f"span_spread_px={span.span_spread_px} exceeds valid maximum {policy.valid_max_span_spread_px}")
    if span.left_edge_spread_px > policy.valid_max_edge_spread_px:
        invalid_reasons.append(f"left_edge_spread_px={span.left_edge_spread_px} exceeds valid maximum {policy.valid_max_edge_spread_px}")
    if span.right_edge_spread_px > policy.valid_max_edge_spread_px:
        invalid_reasons.append(f"right_edge_spread_px={span.right_edge_spread_px} exceeds valid maximum {policy.valid_max_edge_spread_px}")
    if policy.valid_min_edge_contrast > 0:
        if span.min_edge_contrast is None:
            invalid_reasons.append("edge contrast was not measurable")
        elif span.min_edge_contrast < policy.valid_min_edge_contrast:
            invalid_reasons.append(f"min_edge_contrast={span.min_edge_contrast:.1f} below valid minimum {policy.valid_min_edge_contrast:.1f}")
    if policy.valid_min_edge_sharpness > 0:
        if span.min_edge_sharpness is None:
            invalid_reasons.append("edge sharpness was not measurable")
        elif span.min_edge_sharpness < policy.valid_min_edge_sharpness:
            invalid_reasons.append(f"min_edge_sharpness={span.min_edge_sharpness:.1f} below valid minimum {policy.valid_min_edge_sharpness:.1f}")
    if invalid_reasons:
        return GeometryQualityResult(policy.policy_id, GeometryQualityStatus.INVALID, tuple(invalid_reasons))

    degraded_reasons: list[str] = []
    if span.sampled_rows < policy.high_confidence_min_rows:
        degraded_reasons.append(f"sampled_rows={span.sampled_rows} below high-confidence minimum {policy.high_confidence_min_rows}")
    if span.span_spread_px > policy.high_confidence_max_span_spread_px:
        degraded_reasons.append(f"span_spread_px={span.span_spread_px} exceeds high-confidence maximum {policy.high_confidence_max_span_spread_px}")
    if span.left_edge_spread_px > policy.high_confidence_max_edge_spread_px:
        degraded_reasons.append(f"left_edge_spread_px={span.left_edge_spread_px} exceeds high-confidence maximum {policy.high_confidence_max_edge_spread_px}")
    if span.right_edge_spread_px > policy.high_confidence_max_edge_spread_px:
        degraded_reasons.append(f"right_edge_spread_px={span.right_edge_spread_px} exceeds high-confidence maximum {policy.high_confidence_max_edge_spread_px}")
    if policy.high_confidence_min_edge_contrast > 0 and span.min_edge_contrast is not None and span.min_edge_contrast < policy.high_confidence_min_edge_contrast:
        degraded_reasons.append(f"min_edge_contrast={span.min_edge_contrast:.1f} below high-confidence minimum {policy.high_confidence_min_edge_contrast:.1f}")
    if policy.high_confidence_min_edge_sharpness > 0 and span.min_edge_sharpness is not None and span.min_edge_sharpness < policy.high_confidence_min_edge_sharpness:
        degraded_reasons.append(f"min_edge_sharpness={span.min_edge_sharpness:.1f} below high-confidence minimum {policy.high_confidence_min_edge_sharpness:.1f}")
    if degraded_reasons:
        return GeometryQualityResult(policy.policy_id, GeometryQualityStatus.DEGRADED, tuple(degraded_reasons))

    return GeometryQualityResult(policy.policy_id, GeometryQualityStatus.HIGH_CONFIDENCE, ("geometry satisfied all configured high-confidence gates",))
