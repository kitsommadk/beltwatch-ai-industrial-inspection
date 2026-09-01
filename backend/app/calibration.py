"""Calibration and linear-position domain primitives for BeltWatch.

These objects intentionally avoid OpenCV/hardware dependencies. They establish the
contracts needed to map image-space measurements to physical belt dimensions and
associate captured evidence with a repeatable linear position.
"""

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Protocol


@dataclass(frozen=True)
class CalibrationProfile:
    profile_id: str
    camera_id: str
    version: int
    pixels_per_inch: float
    reference_width_in: float
    created_at: datetime

    def inches_from_pixels(self, pixels: float) -> float:
        if self.pixels_per_inch <= 0:
            raise ValueError("pixels_per_inch must be greater than zero")
        if pixels < 0:
            raise ValueError("pixels must not be negative")
        return pixels / self.pixels_per_inch

    def pixels_from_inches(self, inches: float) -> float:
        if self.pixels_per_inch <= 0:
            raise ValueError("pixels_per_inch must be greater than zero")
        if inches < 0:
            raise ValueError("inches must not be negative")
        return inches * self.pixels_per_inch


@dataclass(frozen=True)
class PositionSample:
    position_ft: float
    sampled_at: datetime
    source: str


class PositionProvider(Protocol):
    def sample(self) -> PositionSample: ...


class SimulatedPositionProvider:
    """Deterministic position source used until an encoder/PLC read-only adapter exists."""

    def __init__(self, start_ft: float = 0.0, step_ft: float = 1.0) -> None:
        if step_ft < 0:
            raise ValueError("step_ft must not be negative")
        self._position_ft = start_ft
        self._step_ft = step_ft

    def sample(self) -> PositionSample:
        sample = PositionSample(
            position_ft=round(self._position_ft, 4),
            sampled_at=datetime.now(timezone.utc),
            source="simulated",
        )
        self._position_ft += self._step_ft
        return sample


def make_calibration_profile(
    profile_id: str,
    camera_id: str,
    version: int,
    observed_reference_width_px: float,
    reference_width_in: float,
) -> CalibrationProfile:
    if observed_reference_width_px <= 0:
        raise ValueError("observed_reference_width_px must be greater than zero")
    if reference_width_in <= 0:
        raise ValueError("reference_width_in must be greater than zero")
    if version < 1:
        raise ValueError("version must be at least 1")

    return CalibrationProfile(
        profile_id=profile_id,
        camera_id=camera_id,
        version=version,
        pixels_per_inch=observed_reference_width_px / reference_width_in,
        reference_width_in=reference_width_in,
        created_at=datetime.now(timezone.utc),
    )
