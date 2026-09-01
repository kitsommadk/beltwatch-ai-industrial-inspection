from datetime import datetime, timedelta, timezone

import pytest

from app.camera import SimulatedCamera


class FakeClock:
    def __init__(self) -> None:
        self.current = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)

    def __call__(self) -> datetime:
        return self.current

    def advance(self, seconds: float) -> None:
        self.current += timedelta(seconds=seconds)


def test_simulated_camera_capture_and_health():
    camera = SimulatedCamera("top")

    first = camera.capture()
    second = camera.capture()

    assert first.camera_id == "top"
    assert first.sequence == 1
    assert second.sequence == 2
    assert first.payload_ref == "sim://top/1"
    assert second.payload_ref == "sim://top/2"

    health = camera.health()
    assert health.connected is True
    assert health.stale is False
    assert health.frames_captured == 2
    assert health.capture_failures == 0
    assert health.last_frame_at == second.captured_at


def test_camera_becomes_stale_after_threshold_and_recovers_on_new_frame():
    clock = FakeClock()
    camera = SimulatedCamera("top", stale_after_s=2.0, clock=clock)

    camera.capture()
    clock.advance(2.1)
    assert camera.health().stale is True

    camera.capture()
    assert camera.health().stale is False


def test_disconnected_camera_rejects_capture_counts_failure_and_recovers():
    camera = SimulatedCamera("bottom")
    camera.disconnect()

    with pytest.raises(RuntimeError, match="disconnected"):
        camera.capture()

    health = camera.health()
    assert health.connected is False
    assert health.stale is False
    assert health.capture_failures == 1

    camera.reconnect()
    packet = camera.capture()
    assert packet.camera_id == "bottom"
    assert camera.health().connected is True


def test_camera_configuration_rejects_invalid_health_settings():
    with pytest.raises(ValueError):
        SimulatedCamera("")
    with pytest.raises(ValueError):
        SimulatedCamera("top", width_px=0)
    with pytest.raises(ValueError):
        SimulatedCamera("top", stale_after_s=0)
