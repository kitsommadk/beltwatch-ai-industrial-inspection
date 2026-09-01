"""Hardware-independent belt edge-span estimation.

These estimators are deterministic development baselines for replay and generated
fixture validation. They are not production-validated metrology.
"""

from dataclasses import dataclass
from numbers import Number
from statistics import median
from typing import Any, Protocol

from .camera import FramePacket

EDGE_CONTRAST_WINDOW_PX = 3
EDGE_SHARPNESS_WINDOW_PX = 3


@dataclass(frozen=True)
class BeltSpan:
    left_x: int
    right_x_exclusive: int
    span_px: int
    row_y: int
    threshold: float
    sampled_rows: int = 1
    span_spread_px: int = 0
    left_edge_spread_px: int = 0
    right_edge_spread_px: int = 0
    min_edge_contrast: float | None = None
    min_edge_sharpness: float | None = None


class SpanEstimator(Protocol):
    def estimate(self, frame: FramePacket) -> BeltSpan: ...


def _dimensions(image: Any) -> tuple[int, int]:
    shape = getattr(image, "shape", None)
    if shape is not None and len(shape) >= 2:
        return int(shape[1]), int(shape[0])
    if not image or not image[0]:
        raise ValueError("image must not be empty")
    return len(image[0]), len(image)


def _intensity(pixel: Any) -> float:
    if isinstance(pixel, Number):
        return float(pixel)
    try:
        values = [float(value) for value in pixel]
    except TypeError as exc:
        raise ValueError("unsupported pixel format") from exc
    if not values:
        raise ValueError("pixel channel list must not be empty")
    return sum(values) / len(values)


def _edge_contrast(row: Any, left: int, right: int, width: int) -> float | None:
    """Return the weaker of the left/right local intensity transitions."""
    w = EDGE_CONTRAST_WINDOW_PX
    if left < w or right + w > width or right - left < w:
        return None
    left_bg = median(_intensity(row[x]) for x in range(left - w, left))
    left_belt = median(_intensity(row[x]) for x in range(left, left + w))
    right_belt = median(_intensity(row[x]) for x in range(right - w, right))
    right_bg = median(_intensity(row[x]) for x in range(right, right + w))
    return float(min(abs(left_bg - left_belt), abs(right_bg - right_belt)))


def _edge_sharpness(row: Any, left: int, right: int, width: int) -> float | None:
    """Return the weakest peak adjacent-pixel gradient around either detected edge."""
    w = EDGE_SHARPNESS_WINDOW_PX
    if left < w or right + w > width or right - left < w:
        return None

    def peak_gradient(center: int) -> float:
        start = max(1, center - w)
        stop = min(width - 1, center + w)
        return max(abs(_intensity(row[x]) - _intensity(row[x - 1])) for x in range(start, stop + 1))

    return float(min(peak_gradient(left), peak_gradient(right)))


def estimate_dark_belt_span(image: Any, *, row_fraction: float = 0.5, threshold: float = 100.0, min_run_px: int = 20) -> BeltSpan:
    if not 0 <= row_fraction <= 1:
        raise ValueError("row_fraction must be between 0 and 1")
    if min_run_px <= 0:
        raise ValueError("min_run_px must be greater than zero")
    width, height = _dimensions(image)
    row_y = min(height - 1, int(round((height - 1) * row_fraction)))
    row = image[row_y]
    best: tuple[int, int] | None = None
    start: int | None = None
    for x in range(width):
        dark = _intensity(row[x]) < threshold
        if dark and start is None:
            start = x
        if not dark and start is not None:
            if best is None or x - start > best[1] - best[0]:
                best = (start, x)
            start = None
    if start is not None and (best is None or width - start > best[1] - best[0]):
        best = (start, width)
    if best is None or best[1] - best[0] < min_run_px:
        raise ValueError("no belt-like dark span found on scanline")
    contrast = _edge_contrast(row, best[0], best[1], width)
    sharpness = _edge_sharpness(row, best[0], best[1], width)
    return BeltSpan(best[0], best[1], best[1] - best[0], row_y, float(threshold), min_edge_contrast=contrast, min_edge_sharpness=sharpness)


class DarkScanlineEstimator:
    def __init__(self, *, row_fraction: float = 0.5, threshold: float = 100.0, min_run_px: int = 20) -> None:
        self.row_fraction = row_fraction
        self.threshold = threshold
        self.min_run_px = min_run_px

    def estimate(self, frame: FramePacket) -> BeltSpan:
        if frame.payload is None:
            raise ValueError("frame has no image payload for edge estimation")
        span = estimate_dark_belt_span(frame.payload, row_fraction=self.row_fraction, threshold=self.threshold, min_run_px=self.min_run_px)
        if span.right_x_exclusive > frame.width_px:
            raise ValueError("estimated span exceeds declared frame width")
        return span


class MultiRowDarkEstimator:
    """Aggregate rows and retain width, edge-position, contrast, and sharpness signals."""

    def __init__(self, *, row_fractions: tuple[float, ...] = (0.25, 0.375, 0.5, 0.625, 0.75), threshold: float = 100.0, min_run_px: int = 20, min_valid_rows: int = 3, max_span_spread_px: int | None = 12) -> None:
        if not row_fractions:
            raise ValueError("row_fractions must not be empty")
        if any(not 0 <= row <= 1 for row in row_fractions):
            raise ValueError("row fractions must be between 0 and 1")
        if min_valid_rows <= 0 or min_valid_rows > len(row_fractions):
            raise ValueError("min_valid_rows must fit within row_fractions")
        if max_span_spread_px is not None and max_span_spread_px < 0:
            raise ValueError("max_span_spread_px must be zero or greater")
        self.row_fractions = row_fractions
        self.threshold = threshold
        self.min_run_px = min_run_px
        self.min_valid_rows = min_valid_rows
        self.max_span_spread_px = max_span_spread_px

    def estimate(self, frame: FramePacket) -> BeltSpan:
        if frame.payload is None:
            raise ValueError("frame has no image payload for edge estimation")
        spans: list[BeltSpan] = []
        for row_fraction in self.row_fractions:
            try:
                spans.append(estimate_dark_belt_span(frame.payload, row_fraction=row_fraction, threshold=self.threshold, min_run_px=self.min_run_px))
            except ValueError:
                continue
        if len(spans) < self.min_valid_rows:
            raise ValueError(f"insufficient valid belt rows: {len(spans)} found, {self.min_valid_rows} required")
        widths = [s.span_px for s in spans]
        lefts = [s.left_x for s in spans]
        rights = [s.right_x_exclusive for s in spans]
        contrasts = [s.min_edge_contrast for s in spans if s.min_edge_contrast is not None]
        sharpnesses = [s.min_edge_sharpness for s in spans if s.min_edge_sharpness is not None]
        span_spread = max(widths) - min(widths)
        left_spread = max(lefts) - min(lefts)
        right_spread = max(rights) - min(rights)
        if self.max_span_spread_px is not None and span_spread > self.max_span_spread_px:
            raise ValueError(f"belt span is inconsistent across rows: spread={span_spread}px exceeds {self.max_span_spread_px}px")
        left = int(round(median(lefts)))
        right = int(round(median(rights)))
        if right <= left:
            raise ValueError("aggregated belt span is invalid")
        if right > frame.width_px:
            raise ValueError("estimated span exceeds declared frame width")
        return BeltSpan(
            left_x=left,
            right_x_exclusive=right,
            span_px=right-left,
            row_y=int(round(median(s.row_y for s in spans))),
            threshold=float(self.threshold),
            sampled_rows=len(spans),
            span_spread_px=span_spread,
            left_edge_spread_px=left_spread,
            right_edge_spread_px=right_spread,
            min_edge_contrast=min(contrasts) if len(contrasts) == len(spans) else None,
            min_edge_sharpness=min(sharpnesses) if len(sharpnesses) == len(spans) else None,
        )
