import pytest

from app.runtime import RuntimeConfigurationError, build_runtime


def test_simulation_runtime_exposes_top_and_bottom_services():
    runtime = build_runtime("simulation")

    assert runtime.mode == "simulation"
    assert runtime.service_for("top").calibration.camera_id == "top"
    assert runtime.service_for("bottom").calibration.camera_id == "bottom"


def test_unknown_camera_fails_explicitly():
    runtime = build_runtime("simulation")

    with pytest.raises(RuntimeConfigurationError):
        runtime.service_for("side")


def test_non_simulated_mode_never_falls_back_to_simulation():
    with pytest.raises(RuntimeConfigurationError, match="refusing simulated fallback"):
        build_runtime("pilot")
