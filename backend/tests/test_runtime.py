import pytest

from app.runtime import RuntimeConfigurationError, build_runtime


def test_simulation_runtime_exposes_top_and_bottom_services():
    runtime = build_runtime("simulation")

    assert runtime.mode == "simulation"
    assert runtime.service_for("top").calibration.camera_id == "top"
    assert runtime.service_for("bottom").calibration.camera_id == "bottom"


def test_replay_runtime_exposes_image_driven_estimators():
    runtime = build_runtime("replay")

    assert runtime.mode == "replay"
    assert runtime.service_for("top").calibration.profile_id == "top-replay-v1"
    assert runtime.estimator_for("top") is not None
    assert runtime.estimator_for("bottom") is not None


def test_simulation_mode_does_not_pretend_automatic_image_estimation_exists():
    runtime = build_runtime("simulation")

    with pytest.raises(RuntimeConfigurationError, match="automatic span estimation"):
        runtime.estimator_for("top")


def test_unknown_camera_fails_explicitly():
    runtime = build_runtime("simulation")

    with pytest.raises(RuntimeConfigurationError):
        runtime.service_for("side")


def test_pilot_mode_never_falls_back_to_simulation_or_replay():
    with pytest.raises(RuntimeConfigurationError, match="refusing simulated fallback"):
        build_runtime("pilot")
