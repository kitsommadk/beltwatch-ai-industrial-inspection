from datetime import datetime, timezone

import pytest

from app.calibration import SimulatedPositionProvider, make_calibration_profile
from app.camera import FramePacket
from app.evidence import EvidenceService
from app.frame_quality import FrameQualityError, FrameQualityPolicy, FrameQualityStatus


class OneFrameCamera:
    def __init__(self, frame: FramePacket) -> None:
        self.frame = frame

    def capture(self) -> FramePacket:
        return self.frame


class NeverCalledEstimator:
    def estimate(self, frame: FramePacket):
        raise AssertionError("geometry estimator must not run when frame quality fails")


class StableEstimator:
    provenance_id = "stable-test-v1"

    def estimate(self, frame: FramePacket):
        from app.edge_span import BeltSpan
        return BeltSpan(20, 100, 80, 10, 100.0, sampled_rows=3, min_edge_contrast=180.0, min_edge_sharpness=180.0)


def _frame(background: int, belt: int) -> FramePacket:
    row = tuple([background] * 20 + [belt] * 80 + [background] * 20)
    image = (row,) * 20
    return FramePacket(
        camera_id="top",
        sequence=1,
        captured_at=datetime.now(timezone.utc),
        width_px=120,
        height_px=20,
        payload_ref="generated://frame-quality",
        payload=image,
    )


def _service(frame: FramePacket) -> EvidenceService:
    calibration = make_calibration_profile(
        profile_id="top-test-v1",
        camera_id="top",
        version=1,
        observed_reference_width_px=80.0,
        reference_width_in=4.0,
    )
    return EvidenceService(OneFrameCamera(frame), SimulatedPositionProvider(), calibration)


def _policy() -> FrameQualityPolicy:
    return FrameQualityPolicy(
        policy_id="auto-frame-quality-v1",
        high_confidence_min_dynamic_range=80.0,
        valid_min_dynamic_range=30.0,
    )


def test_low_dynamic_range_fails_before_geometry_estimation():
    service = _service(_frame(130, 80))
    with pytest.raises(FrameQualityError) as exc:
        service.capture_width_auto(
            NeverCalledEstimator(),
            target_width_in=4.0,
            warning_tolerance_in=0.1,
            fail_tolerance_in=0.2,
            frame_quality_policy=_policy(),
        )
    assert exc.value.result.status == FrameQualityStatus.DEGRADED


def test_high_quality_frame_provenance_is_attached_to_automatic_evidence():
    service = _service(_frame(220, 40))
    evidence = service.capture_width_auto(
        StableEstimator(),
        target_width_in=4.0,
        warning_tolerance_in=0.1,
        fail_tolerance_in=0.2,
        frame_quality_policy=_policy(),
    )
    assert evidence.frame_quality is not None
    assert evidence.frame_quality.status == FrameQualityStatus.HIGH_CONFIDENCE
    assert evidence.frame_quality.dynamic_range == 180.0
