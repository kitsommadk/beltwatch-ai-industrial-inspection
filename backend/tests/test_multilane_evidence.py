from datetime import datetime, timezone

from app.calibration import CalibrationProfile, PositionSample
from app.camera import FramePacket
from app.evidence import EvidenceService
from app.multilane_evidence import capture_two_lane_width_auto
from app.multilane_span import TwoLaneDarkEstimator


def _image(width=120, height=40):
    image = [[220 for _ in range(width)] for _ in range(height)]
    for y in range(height):
        for x in range(10, 45):
            image[y][x] = 40
        for x in range(70, 110):
            image[y][x] = 40
    return image


class OneFrameCamera:
    def __init__(self):
        self.calls = 0

    def capture(self):
        self.calls += 1
        return FramePacket(
            camera_id="top",
            sequence=7,
            captured_at=datetime(2026, 9, 1, 15, 30, tzinfo=timezone.utc),
            width_px=120,
            height_px=40,
            payload_ref="generated://slit-frame-7",
            payload=_image(),
        )


class OnePosition:
    def __init__(self):
        self.calls = 0

    def sample(self):
        self.calls += 1
        return PositionSample(position_ft=125.5, source="test-position")


def _service():
    camera = OneFrameCamera()
    position = OnePosition()
    calibration = CalibrationProfile(
        profile_id="top-test-v1",
        camera_id="top",
        version=1,
        pixels_per_inch=10.0,
        reference_width_in=12.0,
    )
    return EvidenceService(camera, position, calibration), camera, position


def test_two_lanes_are_measured_from_one_frame_and_one_position():
    service, camera, position = _service()
    lane_a, lane_b = capture_two_lane_width_auto(
        service,
        TwoLaneDarkEstimator(),
        {"belt-a": 3.5, "belt-b": 4.0},
        warning_tolerance_in=0.05,
        fail_tolerance_in=0.10,
    )

    assert camera.calls == 1
    assert position.calls == 1
    assert lane_a.lane_id == "belt-a"
    assert lane_b.lane_id == "belt-b"
    assert lane_a.evidence.measured_span_px == 35
    assert lane_b.evidence.measured_span_px == 40
    assert lane_a.evidence.width.measured_width_in == 3.5
    assert lane_b.evidence.width.measured_width_in == 4.0
    assert lane_a.evidence.width.status.value == "PASS"
    assert lane_b.evidence.width.status.value == "PASS"
    assert lane_a.evidence.frame_sequence == lane_b.evidence.frame_sequence == 7
    assert lane_a.evidence.payload_ref == lane_b.evidence.payload_ref == "generated://slit-frame-7"
    assert lane_a.evidence.position_ft == lane_b.evidence.position_ft == 125.5
    assert lane_a.evidence.frame_quality == lane_b.evidence.frame_quality
    assert lane_a.evidence.geometry.estimator_id.endswith(":belt-a")
    assert lane_b.evidence.geometry.estimator_id.endswith(":belt-b")


def test_two_lane_targets_may_be_different_widths():
    service, _, _ = _service()
    lane_a, lane_b = capture_two_lane_width_auto(
        service,
        TwoLaneDarkEstimator(),
        {"belt-a": 3.4, "belt-b": 4.0},
        warning_tolerance_in=0.05,
        fail_tolerance_in=0.10,
    )
    assert lane_a.evidence.width.target_width_in == 3.4
    assert lane_a.evidence.width.status.value == "WARNING"
    assert lane_b.evidence.width.target_width_in == 4.0
    assert lane_b.evidence.width.status.value == "PASS"


def test_two_lane_capture_requires_both_lane_targets():
    service, camera, position = _service()
    try:
        capture_two_lane_width_auto(
            service,
            TwoLaneDarkEstimator(),
            {"belt-a": 3.5},
            warning_tolerance_in=0.05,
            fail_tolerance_in=0.10,
        )
        assert False, "missing belt-b target must fail closed"
    except ValueError as exc:
        assert "belt-a and belt-b" in str(exc)
    assert camera.calls == 0
    assert position.calls == 0
