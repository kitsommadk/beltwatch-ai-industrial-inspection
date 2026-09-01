"""Camera ingestion boundary for BeltWatch.

Phase 1 starts with a simulated provider so camera health, timestamps, stale-feed
behavior, and frame contracts can be tested before hardware-specific dependencies
are introduced.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from itertools import count
from typing import Any, Callable, Protocol


Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(frozen=True)
class FramePacket:
    camera_id: str
    sequence: int
    captured_at: datetime
    width_px: int
    height_px: int
    payload_ref: str
    payload: Any | None = field(default=None, repr=False, compare=False)


@dataclass(frozen=True)
class CameraHealth:
    camera_id: str
    connected: bool
    stale: bool
    frames_captured: int
    capture_failures: int
    last_frame_at: datetime | None
    stale_after_s: float


class CameraProvider(Protocol):
    def capture(self) -> FramePacket: ...

    def health(self) -> CameraHealth: ...


class SimulatedCamera:
    """Synthetic frame source implementing the same contract as future UVC cameras.

    The injectable clock makes stale-feed behavior deterministic in tests and gives
    future hardware adapters a clear health contract to follow.
    """

    def __init__(
        self,
        camera_id: str,
        width_px: int = 1920,
        height_px: int = 1080,
        *,
        stale_after_s: float = 2.0,
        clock: Clock = utc_now,
    ) -> None:
        if not camera_id.strip():
            raise ValueError("camera_id must not be empty")
        if width_px <= 0 or height_px <= 0:
            raise ValueError("camera dimensions must be greater than zero")
        if stale_after_s <= 0:
            raise ValueError("stale_after_s must be greater than zero")

        self.camera_id = camera_id
        self.width_px = width_px
        self.height_px = height_px
        self.stale_after_s = float(stale_after_s)
        self._clock = clock
        self._sequence = count(1)
        self._frames_captured = 0
        self._capture_failures = 0
        self._last_frame_at: datetime | None = None
        self._connected = True

    def capture(self) -> FramePacket:
        if not self._connected:
            self._capture_failures += 1
            raise RuntimeError(f"camera {self.camera_id} is disconnected")

        captured_at = self._clock()
        sequence = next(self._sequence)
        self._frames_captured += 1
        self._last_frame_at = captured_at

        return FramePacket(
            camera_id=self.camera_id,
            sequence=sequence,
            captured_at=captured_at,
            width_px=self.width_px,
            height_px=self.height_px,
            payload_ref=f"sim://{self.camera_id}/{sequence}",
        )

    def health(self) -> CameraHealth:
        stale = False
        if self._connected and self._last_frame_at is not None:
            stale = self._clock() - self._last_frame_at > timedelta(seconds=self.stale_after_s)

        return CameraHealth(
            camera_id=self.camera_id,
            connected=self._connected,
            stale=stale,
            frames_captured=self._frames_captured,
            capture_failures=self._capture_failures,
            last_frame_at=self._last_frame_at,
            stale_after_s=self.stale_after_s,
        )

    def disconnect(self) -> None:
        self._connected = False

    def reconnect(self) -> None:
        self._connected = True
