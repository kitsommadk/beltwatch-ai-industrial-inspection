from app.calibration import SimulatedPositionProvider, make_calibration_profile
from app.camera import SimulatedCamera
from app.evidence import EvidenceService


def make_service(camera_id: str = "Top") -> EvidenceService:
    calibration = make_calibration_profile(
        profile_id="top-cal-v1",
        camera_id="Top",
        version=1,
        observed_reference_width_px=960,
        reference_width_in=48,
    )
    return EvidenceService(
        camera=SimulatedCamera(camera_id),
        position=SimulatedPositionProvider(start_ft=125.5, step_ft=1.0),
        calibration=calibration,
    )


def test_capture_width_preserves_traceability():
    evidence = make_service().capture_width(
        measured_span_px=958,
        target_width_in=48.0,
        warning_tolerance_in=0.10,
        fail_tolerance_in=0.20,
    )

    assert evidence.camera_id == "Top"
    assert evidence.frame_sequence == 1
    assert evidence.position_ft == 125.5
    assert evidence.position_source == "simulated"
    assert evidence.calibration_profile_id == "top-cal-v1"
    assert evidence.calibration_version == 1
    assert evidence.measured_span_px == 958
    assert evidence.width.measured_width_in == 47.9
    assert evidence.width.status == "PASS"


def test_capture_width_sequences_frames_and_positions():
    service = make_service()
    first = service.capture_width(960, 48.0, 0.10, 0.20)
    second = service.capture_width(956, 48.0, 0.10, 0.20)

    assert first.frame_sequence == 1
    assert second.frame_sequence == 2
    assert first.position_ft == 125.5
    assert second.position_ft == 126.5


def test_camera_calibration_mismatch_rejected():
    service = make_service(camera_id="Bottom")

    try:
        service.capture_width(960, 48.0, 0.10, 0.20)
        assert False, "expected mismatch to raise"
    except ValueError as exc:
        assert "do not match" in str(exc)
