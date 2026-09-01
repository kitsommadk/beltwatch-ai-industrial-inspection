"""Hardware-independent multi-lane belt span estimation for slit runs."""

from dataclasses import dataclass
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


def _sample_rows(height: int, row_fraction: float, sample_count: int) -> list[int]:
    if not 0 <= row_fraction <= 1:
        raise ValueError("row_fraction must be between 0 and 1")
    if sample_count < 1:
        raise ValueError("sample_count must be at least 1")
    center = (height - 1) * row_fraction
    if sample_count == 1:
        return [int(round(center))]
    half_window = min((height - 1) * 0.2, max(1.0, (height - 1) / 2))
    start = max(0.0, center - half_window)
    end = min(float(height - 1), center + half_window)
    return sorted({int(round(start + (end - start) * i / (sample_count - 1))) for i in range(sample_count)})


def estimate_two_dark_belts(image: Any, *, row_fraction: float = 0.5, threshold: float = 100.0, min_run_px: int = 20, sample_count: int = 5) -> MultiLaneSpan:
    """Estimate two stable belt lanes using several rows instead of one scanline.

    Every sampled row must contain exactly two belt-like dark runs. Runs are
    associated left-to-right within each row, then median edges form Belt A/B.
    Ambiguous or missing rows fail closed rather than manufacturing a width.
    """
    width, height = _dimensions(image)
    rows = _sample_rows(height, row_fraction, sample_count)
    observations: list[tuple[int, list[tuple[int, int]]]] = []
    for row_y in rows:
        runs = sorted(_dark_runs(image[row_y], width, threshold, min_run_px))
        if len(runs) != 2:
            raise ValueError(f"expected exactly two belt-like spans at row {row_y}, found {len(runs)}")
        observations.append((row_y, runs))

    lanes: list[LaneSpan] = []
    representative_row = int(round(median([row_y for row_y, _ in observations])))
    for lane_index, lane_id in enumerate(("belt-a", "belt-b")):
        lefts = [runs[lane_index][0] for _, runs in observations]
        rights = [runs[lane_index][1] for _, runs in observations]
        widths = [right-left for left, right in zip(lefts, rights)]
        left = int(round(median(lefts)))
        right = int(round(median(rights)))
        if right <= left:
            raise ValueError(f"invalid aggregated span for {lane_id}")
        row = image[representative_row]
        lanes.append(LaneSpan(lane_id=lane_id, span=BeltSpan(
            left_x=left,
            right_x_exclusive=right,
            span_px=right-left,
            row_y=representative_row,
            threshold=float(threshold),
            sampled_rows=len(observations),
            span_spread_px=max(widths)-min(widths),
            left_edge_spread_px=max(lefts)-min(lefts),
            right_edge_spread_px=max(rights)-min(rights),
            min_edge_contrast=_edge_contrast(row,left,right,width),
            min_edge_sharpness=_edge_sharpness(row,left,right,width),
        )))
    return MultiLaneSpan(tuple(lanes))


class TwoLaneDarkEstimator:
    """Deterministic two-belt baseline for slit runs.

    Belt A is the left-most belt in image coordinates and Belt B the right-most.
    This remains a replay/software convention pending physical qualification.
    """
    def __init__(self, *, row_fraction: float = 0.5, threshold: float = 100.0, min_run_px: int = 20, sample_count: int = 5) -> None:
        self.row_fraction=row_fraction; self.threshold=threshold; self.min_run_px=min_run_px; self.sample_count=sample_count

    def estimate(self, frame: FramePacket) -> MultiLaneSpan:
        if frame.payload is None:
            raise ValueError("frame has no image payload for multi-lane estimation")
        result=estimate_two_dark_belts(frame.payload,row_fraction=self.row_fraction,threshold=self.threshold,min_run_px=self.min_run_px,sample_count=self.sample_count)
        if any(lane.span.right_x_exclusive > frame.width_px for lane in result.lanes):
            raise ValueError("estimated lane span exceeds declared frame width")
        return result
