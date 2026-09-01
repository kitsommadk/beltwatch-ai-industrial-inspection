from app.camera import SimulatedCamera


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
    assert health.frames_captured == 2
    assert health.last_frame_at == second.captured_at


def test_disconnected_camera_rejects_capture_and_recovers():
    camera = SimulatedCamera("bottom")
    camera.disconnect()

    try:
        camera.capture()
        assert False, "capture should fail when camera is disconnected"
    except RuntimeError:
        pass

    camera.reconnect()
    packet = camera.capture()
    assert packet.camera_id == "bottom"
    assert camera.health().connected is True
