"""Optional OpenCV/UVC camera provider for BeltWatch pilot hardware.

OpenCV is imported lazily so the lightweight API/test installation does not require
camera dependencies. Tests can inject a small cv2-compatible module instead of
opening physical hardware.
"""

from datetime import timedelta
from itertools import count
from typing import Any

from .camera import CameraHealth, Clock, FramePacket, utc_now


class OpenCVCamera:
    """Read UVC frames through OpenCV while honoring BeltWatch health contracts."""

    def __init__(
        self,
        camera_id: str,
        device: int | str,
        *,
        width_px: int = 1920,
        height_px: int = 1080,
        fps: float = 30.0,
        stale_after_s: float = 2.0,
        reconnect_after_failures: int = 3,
        clock: Clock = utc_now,
        cv2_module: Any | None = None,
    ) -> None:
        if not camera_id.strip():
            raise ValueError("camera_id must not be empty")
        if width_px <= 0 or height_px <= 0 or fps <= 0:
            raise ValueError("requested camera mode must be greater than zero")
        if stale_after_s <= 0:
            raise ValueError("stale_after_s must be greater than zero")
        if reconnect_after_failures < 1:
            raise ValueError("reconnect_after_failures must be at least 1")

        if cv2_module is None:
            try:
                import cv2 as cv2_module  # type: ignore[no-redef]
            except ImportError as exc:
                raise RuntimeError(
                    "OpenCV camera support is not installed; install backend/requirements-cv.txt"
                ) from exc

        self.camera_id = camera_id
        self.device = device
        self.requested_width_px = width_px
        self.requested_height_px = height_px
        self.requested_fps = float(fps)
        self.stale_after_s = float(stale_after_s)
        self.reconnect_after_failures = reconnect_after_failures
        self._clock = clock
        self._cv2 = cv2_module
        self._sequence = count(1)
        self._frames_captured = 0
        self._capture_failures = 0
        self._consecutive_failures = 0
        self._last_frame_at = None
        self._capture = self._open_capture()

    def _open_capture(self):
        capture = self._cv2.VideoCapture(self.device)
        if capture is None or not capture.isOpened():
            if capture is not None:
                capture.release()
            raise RuntimeError(f"camera {self.camera_id} could not open device {self.device!r}")

        capture.set(self._cv2.CAP_PROP_FRAME_WIDTH, self.requested_width_px)
        capture.set(self._cv2.CAP_PROP_FRAME_HEIGHT, self.requested_height_px)
        capture.set(self._cv2.CAP_PROP_FPS, self.requested_fps)
        return capture

    def _reopen(self) -> None:
        if self._capture is not None:
            self._capture.release()
        self._capture = self._open_capture()
        self._consecutive_failures = 0

    def capture(self) -> FramePacket:
        if self._capture is None or not self._capture.isOpened():
            self._capture_failures += 1
            raise RuntimeError(f"camera {self.camera_id} is disconnected")

        ok, frame = self._capture.read()
        if not ok or frame is None:
            self._capture_failures += 1
            self._consecutive_failures += 1
            if self._consecutive_failures >= self.reconnect_after_failures:
                try:
                    self._reopen()
                except RuntimeError:
                    pass
            raise RuntimeError(f"camera {self.camera_id} failed to read a frame")

        captured_at = self._clock()
        sequence = next(self._sequence)
        self._frames_captured += 1
        self._consecutive_failures = 0
        self._last_frame_at = captured_at
        height_px, width_px = frame.shape[:2]

        return FramePacket(
            camera_id=self.camera_id,
            sequence=sequence,
            captured_at=captured_at,
            width_px=int(width_px),
            height_px=int(height_px),
            payload_ref=f"opencv://{self.camera_id}/{sequence}",
            payload=frame,
        )

    def health(self) -> CameraHealth:
        connected = self._capture is not None and bool(self._capture.isOpened())
        stale = False
        if connected and self._last_frame_at is not None:
            stale = self._clock() - self._last_frame_at > timedelta(seconds=self.stale_after_s)

        return CameraHealth(
            camera_id=self.camera_id,
            connected=connected,
            stale=stale,
            frames_captured=self._frames_captured,
            capture_failures=self._capture_failures,
            last_frame_at=self._last_frame_at,
            stale_after_s=self.stale_after_s,
        )

    def close(self) -> None:
        if self._capture is not None:
            self._capture.release()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
