import pytest

from app.runtime import build_runtime


def test_replay_runtime_automatically_measures_generated_geometry():
    runtime = build_runtime("replay")
    service = runtime.service_for("top")
    estimator = runtime.estimator_for("top")

    evidence = service.capture_width_auto(
        estimator=estimator,
        target_width_in=48.0,
        warning_tolerance_in=0.1,
        fail_tolerance_in=0.2,
    )

    assert evidence.payload_ref.startswith("replay://top/1?")
    assert evidence.measured_span_px == 960
    assert evidence.width.measured_width_in == pytest.approx(48.0)
    assert evidence.position_ft == pytest.approx(0.0)


def test_replay_sequence_drives_real_measurement_changes_without_caller_span():
    runtime = build_runtime("replay")
    service = runtime.service_for("top")
    estimator = runtime.estimator_for("top")

    first = service.capture_width_auto(estimator, 48.0, 0.1, 0.2)
    second = service.capture_width_auto(estimator, 48.0, 0.1, 0.2)
    third = service.capture_width_auto(estimator, 48.0, 0.1, 0.2)

    assert [first.measured_span_px, second.measured_span_px, third.measured_span_px] == [960, 958, 962]
    assert second.width.measured_width_in == pytest.approx(47.9)
    assert third.width.measured_width_in == pytest.approx(48.1)
    assert [first.position_ft, second.position_ft, third.position_ft] == [0.0, 1.0, 2.0]


def test_replay_runtime_is_finite_and_reports_end_of_fixture():
    runtime = build_runtime("replay")
    service = runtime.service_for("bottom")
    estimator = runtime.estimator_for("bottom")

    for _ in range(6):
        service.capture_width_auto(estimator, 48.0, 0.1, 0.2)

    with pytest.raises(EOFError, match="end of fixture"):
        service.capture_width_auto(estimator, 48.0, 0.1, 0.2)

    health = service.camera.health()
    assert health.frames_captured == 6
    assert health.capture_failures == 1
