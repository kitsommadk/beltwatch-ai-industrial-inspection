"""Detection boundary used by the pilot.

The current repository intentionally ships with a simulated provider. A camera/
model integration can implement the same interface without changing the event
review workflow or API contract.
"""

from dataclasses import dataclass
from random import Random
from typing import Protocol


@dataclass(frozen=True)
class Detection:
    damage_type: str
    severity: str
    camera: str
    confidence: float
    measured_width_in: float


class DetectionProvider(Protocol):
    def detect(self, kind: str, target_width_in: float, camera: str | None = None) -> Detection: ...


class SimulatedDetector:
    """Deterministic-enough demo provider; not a trained vision model."""

    def __init__(self, seed: int | None = None) -> None:
        self.random = Random(seed)

    def detect(self, kind: str, target_width_in: float, camera: str | None = None) -> Detection:
        selected_camera = camera or self.random.choice(["Top", "Bottom"])
        if kind == "width":
            return Detection(
                damage_type="Width deviation",
                severity="critical",
                camera="Top",
                confidence=round(self.random.uniform(0.94, 0.98), 2),
                measured_width_in=round(target_width_in - self.random.uniform(0.13, 0.19), 2),
            )
        if kind == "surface":
            return Detection(
                damage_type="Surface anomaly",
                severity="info",
                camera="Bottom",
                confidence=round(self.random.uniform(0.78, 0.88), 2),
                measured_width_in=round(target_width_in + self.random.uniform(-0.02, 0.02), 2),
            )
        return Detection(
            damage_type="Edge irregularity",
            severity="warning",
            camera=selected_camera,
            confidence=round(self.random.uniform(0.89, 0.95), 2),
            measured_width_in=round(target_width_in - self.random.uniform(0.05, 0.09), 2),
        )

