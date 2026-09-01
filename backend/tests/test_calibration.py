import pytest

from app.calibration import SimulatedPositionProvider, make_calibration_profile


def test_calibration_maps_pixels_to_inches_and_back():
    profile = make_calibration_profile(
        profile_id="top-v1",
        camera_id="top",
        version=1,
        observed_reference_width_px=960,
        reference_width_in=48,
    )

    assert profile.pixels_per_inch == 20
    assert profile.inches_from_pixels(960) == 48
    assert profile.pixels_from_inches(24) == 480


def test_calibration_rejects_invalid_reference_dimensions():
    with pytest.raises(ValueError):
        make_calibration_profile("bad", "top", 1, 0, 48)

    with pytest.raises(ValueError):
        make_calibration_profile("bad", "top", 1, 960, 0)


def test_simulated_position_provider_advances_repeatably():
    provider = SimulatedPositionProvider(start_ft=10, step_ft=0.5)

    first = provider.sample()
    second = provider.sample()

    assert first.position_ft == 10
    assert second.position_ft == 10.5
    assert first.source == "simulated"
