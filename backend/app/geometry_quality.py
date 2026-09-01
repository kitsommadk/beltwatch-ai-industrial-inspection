"""Deterministic quality gates for image-derived belt geometry.

Geometry quality is separate from dimensional tolerance. A width can be numerically
within tolerance while the image evidence used to derive it is too ambiguous to trust.
"""

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

    def __post_init__(self) -> None:
        if not self.policy_id.strip():
            raise ValueError("policy_id must not be empty")
        if self.valid_min_rows <= 0:
            raise ValueError("valid_min_rows must be greater than zero")
        if self.high_confidence_min_rows < self.valid_min_rows:
            raise ValueError("high_confidence_min_rows must be >= valid_min_rows")
        if self.high_confidence_max_span_spread_px < 0:
            raise ValueError("high_confidence_max_span_spread_px must not be negative")
        if self.valid_max_span_spread_px < self.high_confidence_max_span_spread_px:
            raise ValueError(
                "valid_max_span_spread_px must be >= high_confidence_max_span_spread_px"
            )


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
    policy_id="default-geometry-quality-v1",
    high_confidence_min_rows=1,
    valid_min_rows=1,
    high_confidence_max_span_spread_px=0,
    valid_max_span_spread_px=12,
)


def assess_geometry(span: BeltSpan, policy: GeometryQualityPolicy) -> GeometryQualityResult:
    """Classify geometry as high-confidence, degraded, or invalid.

    The current baseline uses cross-row support and span consistency. Future policies
    may add edge-position spread, contrast, segmentation confidence, or calibration
    validity without changing the downstream evidence contract.
    """
    invalid_reasons: list[str] = []
    if span.sampled_rows < policy.valid_min_rows:
        invalid_reasons.append(
            f"sampled_rows={span.sampled_rows} below valid minimum {policy.valid_min_rows}"
        )
    if span.span_spread_px > policy.valid_max_span_spread_px:
        invalid_reasons.append(
            f"span_spread_px={span.span_spread_px} exceeds valid maximum {policy.valid_max_span_spread_px}"
        )
    if invalid_reasons:
        return GeometryQualityResult(
            policy_id=policy.policy_id,
            status=GeometryQualityStatus.INVALID,
            reasons=tuple(invalid_reasons),
        )

    degraded_reasons: list[str] = []
    if span.sampled_rows < policy.high_confidence_min_rows:
        degraded_reasons.append(
            f"sampled_rows={span.sampled_rows} below high-confidence minimum {policy.high_confidence_min_rows}"
        )
    if span.span_spread_px > policy.high_confidence_max_span_spread_px:
        degraded_reasons.append(
            f"span_spread_px={span.span_spread_px} exceeds high-confidence maximum "
            f"{policy.high_confidence_max_span_spread_px}"
        )
    if degraded_reasons:
        return GeometryQualityResult(
            policy_id=policy.policy_id,
            status=GeometryQualityStatus.DEGRADED,
            reasons=tuple(degraded_reasons),
        )

    return GeometryQualityResult(
        policy_id=policy.policy_id,
        status=GeometryQualityStatus.HIGH_CONFIDENCE,
        reasons=("geometry satisfied all configured high-confidence gates",),
    )
