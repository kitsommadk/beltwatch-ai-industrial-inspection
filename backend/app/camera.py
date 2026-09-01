"""Camera ingestion boundary for BeltWatch.

Phase 1 starts with a simulated provider so camera health, timestamps, and frame
contracts can be tested before introducing hardware-specific dependencies.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from itertools import count
from typing import Protocol


@dataclass(frozen=True)
class FramePacket:
    camera_id: str
    sequence: int
    captured_at: datetime
    width_px: int
    height_px: int
    payload_ref: str


@dataclass(frozen=True)
class CameraHealth:
    camera_id: str
    connected: bool
    stale: bool
    frames_captured: int
    last_frame_at: datetime | None


class CameraProvider(Protocol):
    def capture(self) -> FramePacket: ...

    def health(self) -> CameraHealth: ...


class SimulatedCamera:
    """Synthetic frame source implementing the same contract as future UVC cameras."""

    def __init__(self, camera_id: str, width_px: int = 1920, height_px: int = 1080) -> None:
        self.camera_id = camera_id
        self.width_px = width_px
        self.height_px = height_px
        self._sequence = count(1)
        self._frames_captured = 0
        self._last_frame_at: datetime | None = None
        self._connected = True

    def capture(self) -> FramePacket:
        if not self._connected:
            raise RuntimeError(f"camera {self.camera_id} is disconnected")

        captured_at = datetime.now(timezone.utc)
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
        return CameraHealth(
            camera_id=self.camera_id,
            connected=self._connected,
            stale=False,
            frames_captured=self._frames_captured,
            last_frame_at=self._last_frame_at,
        )

    def disconnect(self) -> None:
        self._connected = False

    def reconnect(self) -> None:
        self._connected = True
