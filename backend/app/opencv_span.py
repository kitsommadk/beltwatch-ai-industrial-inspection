"""Optional OpenCV belt-span estimator for replay benchmarking.

This provider uses classical image processing, not a trained AI model. It is kept
behind the same SpanEstimator contract as the pure-Python baselines so BeltWatch
can compare accuracy and latency on identical fixtures.
"""

from __future__ import annotations

from typing import Any

from .camera import FramePacket
from .edge_span import BeltSpan


class OpenCVContourEstimator:
    """Estimate belt edges from the largest dark connected contour.

    The estimator thresholds a grayscale image, performs a small morphological
    closing operation, finds external contours, and returns the bounding interval
    of the largest contour that meets minimum area/height requirements.
    """

    def __init__(
        self,
        *,
        threshold: float = 100.0,
        min_area_px: float = 2_000.0,
        min_height_fraction: float = 0.25,
        close_kernel_px: int = 5,
        cv2_module: Any | None = None,
    ) -> None:
        if not 0 <= threshold <= 255:
            raise ValueError("threshold must be between 0 and 255")
        if min_area_px <= 0:
            raise ValueError("min_area_px must be greater than zero")
        if not 0 < min_height_fraction <= 1:
            raise ValueError("min_height_fraction must be within (0, 1]")
        if close_kernel_px <= 0:
            raise ValueError("close_kernel_px must be greater than zero")

        self.threshold = float(threshold)
        self.min_area_px = float(min_area_px)
        self.min_height_fraction = float(min_height_fraction)
        self.close_kernel_px = int(close_kernel_px)
        self._cv2 = cv2_module

    def _cv(self):
        if self._cv2 is not None:
            return self._cv2
        try:
            import cv2
        except ImportError as exc:  # pragma: no cover - exercised in non-CV installs
            raise RuntimeError(
                "OpenCV is not installed; install backend/requirements-cv.txt"
            ) from exc
        self._cv2 = cv2
        return cv2

    def estimate(self, frame: FramePacket) -> BeltSpan:
        if frame.payload is None:
            raise ValueError("frame has no image payload for edge estimation")

        cv2 = self._cv()
        image = frame.payload
        shape = getattr(image, "shape", None)
        if shape is None or len(shape) < 2:
            raise ValueError("OpenCV estimator requires a NumPy-compatible image array")
        height, width = int(shape[0]), int(shape[1])
        if width != frame.width_px or height != frame.height_px:
            raise ValueError("image dimensions do not match the frame contract")

        if len(shape) == 2:
            gray = image
        elif len(shape) == 3 and shape[2] == 1:
            gray = image[:, :, 0]
        elif len(shape) == 3 and shape[2] >= 3:
            gray = cv2.cvtColor(image[:, :, :3], cv2.COLOR_BGR2GRAY)
        else:
            raise ValueError("unsupported image shape for OpenCV edge estimation")

        _, binary = cv2.threshold(gray, self.threshold, 255, cv2.THRESH_BINARY_INV)
        kernel = cv2.getStructuringElement(
            cv2.MORPH_RECT, (self.close_kernel_px, self.close_kernel_px)
        )
        binary = cv2.morphologyEx(binary, cv2.MORPH_CLOSE, kernel)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        candidates: list[tuple[float, int, int, int, int]] = []
        min_height_px = height * self.min_height_fraction
        for contour in contours:
            area = float(cv2.contourArea(contour))
            x, y, w, h = cv2.boundingRect(contour)
            if area >= self.min_area_px and h >= min_height_px and w > 0:
                candidates.append((area, x, y, w, h))

        if not candidates:
            raise ValueError("no belt-like contour found")

        _, x, y, w, h = max(candidates, key=lambda item: item[0])
        right = x + w
        if right > frame.width_px:
            raise ValueError("estimated span exceeds declared frame width")

        return BeltSpan(
            left_x=int(x),
            right_x_exclusive=int(right),
            span_px=int(w),
            row_y=int(y + h // 2),
            threshold=self.threshold,
            sampled_rows=int(h),
            span_spread_px=0,
        )
