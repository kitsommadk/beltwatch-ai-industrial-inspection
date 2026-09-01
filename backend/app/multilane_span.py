"""Hardware-independent multi-lane belt span estimation for slit runs."""

from dataclasses import dataclass
from numbers import Number
from statistics import median
from typing import Any

from .camera import FramePacket
from .edge_span import BeltSpan, _dimensions, _edge_contrast, _edge_sharpness, _intensity


@dataclass(frozen=True)
class LaneSpan:
    lane_id: str
    span: BeltSpan


@dataclass(frozen=True)
class MultiLaneSpan:
    lanes: tuple[LaneSpan, ...]

    def __post_init__(self) -> None:
        if not self.lanes:
            raise ValueError("lanes must not be empty")
        ids = [lane.lane_id for lane in self.lanes]
        if len(ids) != len(set(ids)):
            raise ValueError("lane IDs must be unique")
        ordered = sorted(self.lanes, key=lambda lane: lane.span.left_x)
        for left, right in zip(ordered, ordered[1:]):
            if left.span.right_x_exclusive > right.span.left_x:
                raise ValueError("lane spans must not overlap")


def _dark_runs(row: Any, width: int, threshold: float, min_run_px: int) -> list[tuple[int, int]]:
    runs: list[tuple[int, int]] = []
    start: int | None = None
    for x in range(width):
        dark = _intensity(row[x]) < threshold
        if dark and start is None:
            start = x
        elif not dark and start is not None:
            if x - start >= min_run_px:
                runs.append((start, x))
            start = None
    if start is not None and width - start >= min_run_px:
        runs.append((start, width))
    return runs


def estimate_two_dark_belts(image: Any, *, row_fraction: float = 0.5, threshold: float = 100.0, min_run_px: int = 20) -> MultiLaneSpan:
    width, height = _dimensions(image)
    row_y = min(height - 1, int(round((height - 1) * row_fraction)))
    row = image[row_y]
    runs = _dark_runs(row, width, threshold, min_run_px)
    if len(runs) != 2:
        raise ValueError(f"expected exactly two belt-like spans, found {len(runs)}")

    lanes: list[LaneSpan] = []
    for lane_id, (left, right) in zip(("belt-a", "belt-b"), sorted(runs)):
        lanes.append(
            LaneSpan(
                lane_id=lane_id,
                span=BeltSpan(
                    left_x=left,
                    right_x_exclusive=right,
                    span_px=right-left,
                    row_y=row_y,
                    threshold=float(threshold),
                    min_edge_contrast=_edge_contrast(row, left, right, width),
                    min_edge_sharpness=_edge_sharpness(row, left, right, width),
                ),
            )
        )
    return MultiLaneSpan(tuple(lanes))


class TwoLaneDarkEstimator:
    """Deterministic two-belt baseline for slit runs.

    Belt A is defined as the left-most belt in image coordinates and Belt B as the
    right-most belt. This is a software identity convention for replay validation,
    not yet a physically qualified tracking rule.
    """

    def __init__(self, *, row_fraction: float = 0.5, threshold: float = 100.0, min_run_px: int = 20) -> None:
        self.row_fraction = row_fraction
        self.threshold = threshold
        self.min_run_px = min_run_px

    def estimate(self, frame: FramePacket) -> MultiLaneSpan:
        if frame.payload is None:
            raise ValueError("frame has no image payload for multi-lane estimation")
        result = estimate_two_dark_belts(
            frame.payload,
            row_fraction=self.row_fraction,
            threshold=self.threshold,
            min_run_px=self.min_run_px,
        )
        if any(lane.span.right_x_exclusive > frame.width_px for lane in result.lanes):
            raise ValueError("estimated lane span exceeds declared frame width")
        return result
