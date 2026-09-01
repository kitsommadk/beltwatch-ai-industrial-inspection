"""Deterministic frame replay for hardware-free BeltWatch validation.

Replay lets the inspection pipeline exercise real image-shaped payloads from a
curated fixture or recorded run without pretending that a physical camera is live.
"""

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from itertools import count
from pathlib import Path
from typing import Callable, Sequence

from .camera import CameraHealth, FramePacket, utc_now


@dataclass(frozen=True)
class ReplayFrame:
    source_ref: str
    width_px: int
    height_px: int
    payload: object | None = None


class ReplayCamera:
    """Finite deterministic camera provider for validation and regression tests."""

    def __init__(
        self,
        camera_id: str,
        frames: Sequence[ReplayFrame],
        *,
        loop: bool = False,
        stale_after_s: float = 2.0,
        clock: Callable[[], datetime] = utc_now,
    ) -> None:
        if not camera_id.strip():
            raise ValueError("camera_id must not be empty")
        if not frames:
            raise ValueError("at least one replay frame is required")
        if stale_after_s <= 0:
            raise ValueError("stale_after_s must be greater than zero")
        for frame in frames:
            if frame.width_px <= 0 or frame.height_px <= 0:
                raise ValueError("replay frame dimensions must be greater than zero")

        self.camera_id = camera_id
        self.frames = tuple(frames)
        self.loop = loop
        self.stale_after_s = float(stale_after_s)
        self._clock = clock
        self._cursor = 0
        self._sequence = count(1)
        self._frames_captured = 0
        self._capture_failures = 0
        self._last_frame_at: datetime | None = None
        self._connected = True

    def capture(self) -> FramePacket:
        if not self._connected:
            self._capture_failures += 1
            raise RuntimeError(f"replay camera {self.camera_id} is disconnected")
        if self._cursor >= len(self.frames):
            if self.loop:
                self._cursor = 0
            else:
                self._capture_failures += 1
                raise EOFError(f"replay camera {self.camera_id} reached end of fixture")

        fixture = self.frames[self._cursor]
        self._cursor += 1
        sequence = next(self._sequence)
        captured_at = self._clock()
        self._frames_captured += 1
        self._last_frame_at = captured_at
        return FramePacket(
            camera_id=self.camera_id,
            sequence=sequence,
            captured_at=captured_at,
            width_px=fixture.width_px,
            height_px=fixture.height_px,
            payload_ref=f"replay://{self.camera_id}/{sequence}?source={fixture.source_ref}",
            payload=fixture.payload,
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

    @property
    def remaining(self) -> int:
        return max(0, len(self.frames) - self._cursor)

    def disconnect(self) -> None:
        self._connected = False

    def reconnect(self) -> None:
        self._connected = True
