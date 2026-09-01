from datetime import datetime, timedelta, timezone

import pytest

from app.replay import ReplayCamera, ReplayFrame


class MutableClock:
    def __init__(self):
        self.value = datetime(2026, 8, 31, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.value


def frames():
    return [
        ReplayFrame("fixture/nominal-001.png", 1920, 1080, payload={"span_px": 960}),
        ReplayFrame("fixture/warning-001.png", 1920, 1080, payload={"span_px": 958}),
    ]


def test_replay_is_finite_and_traceable():
    camera = ReplayCamera("top", frames())
    first = camera.capture()
    second = camera.capture()

    assert first.sequence == 1
    assert first.payload_ref.startswith("replay://top/1")
    assert first.payload["span_px"] == 960
    assert second.payload["span_px"] == 958
    assert camera.remaining == 0

    with pytest.raises(EOFError):
        camera.capture()
    assert camera.health().capture_failures == 1


def test_replay_can_loop_for_soak_style_tests():
    camera = ReplayCamera("bottom", frames(), loop=True)
    camera.capture()
    camera.capture()
    third = camera.capture()
    assert third.sequence == 3
    assert third.payload["span_px"] == 960


def test_replay_uses_same_stale_health_contract():
    clock = MutableClock()
    camera = ReplayCamera("top", frames(), stale_after_s=1.0, clock=clock)
    camera.capture()
    assert camera.health().stale is False

    clock.value += timedelta(seconds=2)
    assert camera.health().stale is True
