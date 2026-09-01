from datetime import datetime, timezone

import pytest

from app.calibration import SimulatedPositionProvider, make_calibration_profile
from app.camera import CameraHealth, FramePacket
from app.edge_span import BeltSpan
from app.evidence import EvidenceService
from app.geometry_quality import (
    GeometryQualityError,
    GeometryQualityPolicy,
    GeometryQualityStatus,
    assess_geometry,
)


POLICY = GeometryQualityPolicy(
    policy_id="quality-test-v1",
    high_confidence_min_rows=5,
    valid_min_rows=3,
    high_confidence_max_span_spread_px=2,
    valid_max_span_spread_px=12,
)


def span(*, rows=5, spread=0):
    return BeltSpan(
        left_x=120,
        right_x_exclusive=1080,
        span_px=960,
        row_y=40,
        threshold=100,
        sampled_rows=rows,
        span_spread_px=spread,
    )


def test_high_confidence_geometry_meets_all_gates():
    result = assess_geometry(span(rows=5, spread=2), POLICY)
    assert result.status == GeometryQualityStatus.HIGH_CONFIDENCE
    assert result.high_confidence is True


def test_geometry_is_degraded_when_valid_but_not_high_confidence():
    result = assess_geometry(span(rows=4, spread=5), POLICY)
    assert result.status == GeometryQualityStatus.DEGRADED
    assert any("sampled_rows" in reason for reason in result.reasons)
    assert any("span_spread_px" in reason for reason in result.reasons)


def test_geometry_is_invalid_when_minimum_validity_is_not_met():
    result = assess_geometry(span(rows=2, spread=13), POLICY)
    assert result.status == GeometryQualityStatus.INVALID
    assert len(result.reasons) == 2


class FixtureCamera:
    camera_id = "top"

    def capture(self):
        image = tuple((tuple([220] * 120 + [40] * 960 + [220] * 120)) for _ in range(80))
        return FramePacket(
            camera_id="top",
            sequence=1,
            captured_at=datetime.now(timezone.utc),
            width_px=1200,
            height_px=80,
            payload_ref="fixture://quality/1",
            payload=image,
        )

    def health(self):
        return CameraHealth("top", True, False, 1, 0, None, 2.0)


class StaticEstimator:
    provenance_id = "static-quality-test-v1"

    def __init__(self, result_span):
        self.result_span = result_span

    def estimate(self, _frame):
        return self.result_span


def service():
    return EvidenceService(
        camera=FixtureCamera(),
        position=SimulatedPositionProvider(start_ft=10, step_ft=1),
        calibration=make_calibration_profile(
            profile_id="quality-cal-v1",
            camera_id="top",
            version=1,
            observed_reference_width_px=960,
            reference_width_in=48,
        ),
    )


def test_degraded_geometry_cannot_quietly_become_dimensional_pass():
    estimator = StaticEstimator(span(rows=4, spread=5))
    with pytest.raises(GeometryQualityError, match="geometry quality degraded"):
        service().capture_width_auto(
            estimator=estimator,
            quality_policy=POLICY,
            target_width_in=48,
            warning_tolerance_in=0.1,
            fail_tolerance_in=0.2,
        )


def test_diagnostic_workflow_can_explicitly_retain_degraded_provenance():
    estimator = StaticEstimator(span(rows=4, spread=5))
    evidence = service().capture_width_auto(
        estimator=estimator,
        quality_policy=POLICY,
        require_high_confidence=False,
        target_width_in=48,
        warning_tolerance_in=0.1,
        fail_tolerance_in=0.2,
    )
    assert evidence.width.status.value == "PASS"
    assert evidence.geometry is not None
    assert evidence.geometry.quality_status == GeometryQualityStatus.DEGRADED
    assert evidence.geometry.quality_policy_id == "quality-test-v1"
