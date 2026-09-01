from datetime import datetime, timezone

from app.calibration import SimulatedPositionProvider, make_calibration_profile
from app.camera import CameraHealth, FramePacket
from app.edge_span import DarkScanlineEstimator
from app.evidence import EvidenceService
from app.measurement import WidthStatus


def fixture(width=1200, height=80, left=120, belt_width=960):
    image = [[220 for _ in range(width)] for _ in range(height)]
    for y in range(height):
        for x in range(left, left + belt_width):
            image[y][x] = 40
    return image


class FixtureCamera:
    def __init__(self, belt_width=960):
        self.camera_id = "top"
        self._belt_width = belt_width
        self._sequence = 0

    def capture(self):
        self._sequence += 1
        return FramePacket(
            camera_id="top",
            sequence=self._sequence,
            captured_at=datetime.now(timezone.utc),
            width_px=1200,
            height_px=80,
            payload_ref=f"fixture://top/{self._sequence}",
            payload=fixture(belt_width=self._belt_width),
        )

    def health(self):
        return CameraHealth("top", True, False, self._sequence, 0, None, 2.0)


def service(belt_width=960):
    calibration = make_calibration_profile(
        profile_id="fixture-cal-v1",
        camera_id="top",
        version=1,
        observed_reference_width_px=960,
        reference_width_in=48,
    )
    return EvidenceService(
        camera=FixtureCamera(belt_width),
        position=SimulatedPositionProvider(start_ft=50, step_ft=5),
        calibration=calibration,
    )


def test_image_payload_drives_width_without_caller_supplied_span():
    evidence = service(960).capture_width_auto(
        estimator=DarkScanlineEstimator(threshold=100, min_run_px=100),
        target_width_in=48,
        warning_tolerance_in=0.10,
        fail_tolerance_in=0.20,
    )

    assert evidence.measured_span_px == 960
    assert evidence.width.measured_width_in == 48.0
    assert evidence.width.status == WidthStatus.PASS
    assert evidence.payload_ref == "fixture://top/1"
    assert evidence.position_ft == 50


def test_generated_narrow_belt_reaches_warning_classification():
    evidence = service(958).capture_width_auto(
        estimator=DarkScanlineEstimator(threshold=100, min_run_px=100),
        target_width_in=48,
        warning_tolerance_in=0.08,
        fail_tolerance_in=0.16,
    )

    assert evidence.measured_span_px == 958
    assert evidence.width.measured_width_in == 47.9
    assert evidence.width.status == WidthStatus.WARNING
