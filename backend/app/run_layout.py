"""Inspection run layout contracts for single-belt and slit-belt workflows."""

from dataclasses import dataclass
from enum import Enum


class RunLayout(str, Enum):
    SINGLE = "single"
    SLIT_TWO_LANE = "slit-two-lane"


@dataclass(frozen=True)
class LaneDefinition:
    lane_id: str
    display_name: str

    def __post_init__(self) -> None:
        if not self.lane_id.strip():
            raise ValueError("lane_id must not be empty")
        if not self.display_name.strip():
            raise ValueError("display_name must not be empty")


SINGLE_LANES = (LaneDefinition("belt", "Belt"),)
SLIT_TWO_LANES = (
    LaneDefinition("belt-a", "Belt A"),
    LaneDefinition("belt-b", "Belt B"),
)


def lanes_for_layout(layout: RunLayout) -> tuple[LaneDefinition, ...]:
    if layout == RunLayout.SINGLE:
        return SINGLE_LANES
    if layout == RunLayout.SLIT_TWO_LANE:
        return SLIT_TWO_LANES
    raise ValueError(f"unsupported run layout: {layout}")
