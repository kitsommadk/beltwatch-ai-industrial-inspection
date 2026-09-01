from datetime import datetime, timedelta, timezone

import pytest

from app.uvc_camera import OpenCVCamera


class FakeFrame:
    shape = (1080, 1920, 3)


class FakeCapture:
    def __init__(self, reads=None, opened=True):
        self.opened = opened
        self.reads = list(reads or [(True, FakeFrame())])
        self.set_calls = []
        self.released = False

    def isOpened(self):
        return self.opened and not self.released

    def set(self, prop, value):
        self.set_calls.append((prop, value))
        return True

    def read(self):
        if self.reads:
            return self.reads.pop(0)
        return False, None

    def release(self):
        self.released = True


class FakeCV2:
    CAP_PROP_FRAME_WIDTH = 3
    CAP_PROP_FRAME_HEIGHT = 4
    CAP_PROP_FPS = 5

    def __init__(self, captures):
        self.captures = list(captures)
        self.devices = []

    def VideoCapture(self, device):
        self.devices.append(device)
        return self.captures.pop(0)


class FakeClock:
    def __init__(self):
        self.current = datetime(2026, 9, 1, 12, 0, tzinfo=timezone.utc)

    def __call__(self):
        return self.current

    def advance(self, seconds):
        self.current += timedelta(seconds=seconds)


def test_uvc_adapter_configures_device_and_returns_live_payload():
    capture = FakeCapture()
    cv2 = FakeCV2([capture])
    camera = OpenCVCamera("top", 0, cv2_module=cv2, fps=60)

    packet = camera.capture()

    assert cv2.devices == [0]
    assert packet.camera_id == "top"
    assert packet.width_px == 1920
    assert packet.height_px == 1080
    assert packet.payload is not None
    assert packet.payload_ref == "opencv://top/1"
    assert (cv2.CAP_PROP_FRAME_WIDTH, 1920) in capture.set_calls
    assert (cv2.CAP_PROP_FRAME_HEIGHT, 1080) in capture.set_calls
    assert (cv2.CAP_PROP_FPS, 60.0) in capture.set_calls
    assert camera.health().frames_captured == 1


def test_uvc_adapter_reports_stale_frame_using_same_health_contract():
    clock = FakeClock()
    camera = OpenCVCamera("top", 0, cv2_module=FakeCV2([FakeCapture()]), clock=clock, stale_after_s=1)

    camera.capture()
    clock.advance(1.1)

    assert camera.health().stale is True


def test_uvc_adapter_counts_failed_reads_and_reopens_after_threshold():
    first = FakeCapture(reads=[(False, None), (False, None)])
    replacement = FakeCapture(reads=[(True, FakeFrame())])
    cv2 = FakeCV2([first, replacement])
    camera = OpenCVCamera("bottom", 1, cv2_module=cv2, reconnect_after_failures=2)

    with pytest.raises(RuntimeError, match="failed to read"):
        camera.capture()
    with pytest.raises(RuntimeError, match="failed to read"):
        camera.capture()

    assert camera.health().capture_failures == 2
    assert len(cv2.devices) == 2
    packet = camera.capture()
    assert packet.sequence == 1
    assert packet.camera_id == "bottom"


def test_uvc_adapter_fails_if_device_cannot_open():
    cv2 = FakeCV2([FakeCapture(opened=False)])

    with pytest.raises(RuntimeError, match="could not open"):
        OpenCVCamera("top", 0, cv2_module=cv2)
