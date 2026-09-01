"""Generated computer-vision fixtures for hardware-free robustness testing.

These fixtures deliberately model simplified image degradations such as brightness
gradients, sensor-like impulse noise, shadows, and edge damage. They are synthetic
and must not be presented as substitutes for representative physical-camera data.
"""

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class GeneratedBeltFixture:
    image: np.ndarray
    expected_left_x: int
    expected_right_x_exclusive: int
    label: str

    @property
    def expected_span_px(self) -> int:
        return self.expected_right_x_exclusive - self.expected_left_x


def make_belt_fixture(
    *,
    width: int = 1200,
    height: int = 120,
    left: int = 120,
    belt_width: int = 960,
    background: int = 220,
    belt: int = 40,
    brightness_gradient: int = 0,
    shadow_band: tuple[int, int, int] | None = None,
    impulse_noise_fraction: float = 0.0,
    edge_notch: tuple[str, int, int, int] | None = None,
    seed: int = 7,
    label: str = "generated",
) -> GeneratedBeltFixture:
    """Create a deterministic grayscale belt image with optional degradations.

    `shadow_band` is (x_start, x_end, delta_intensity). `edge_notch` is
    (side, y_start, y_end, depth_px), where side is ``left`` or ``right``.
    """
    if width <= 0 or height <= 0 or belt_width <= 0:
        raise ValueError("fixture dimensions must be greater than zero")
    if left < 0 or left + belt_width > width:
        raise ValueError("belt geometry must fit within the image")
    if not 0 <= impulse_noise_fraction <= 1:
        raise ValueError("impulse_noise_fraction must be between zero and one")

    image = np.full((height, width), background, dtype=np.float32)
    image[:, left : left + belt_width] = belt

    if brightness_gradient:
        gradient = np.linspace(-brightness_gradient, brightness_gradient, width, dtype=np.float32)
        image += gradient[None, :]

    if shadow_band is not None:
        x_start, x_end, delta = shadow_band
        if not 0 <= x_start < x_end <= width:
            raise ValueError("shadow band must fit within image width")
        image[:, x_start:x_end] += delta

    if edge_notch is not None:
        side, y_start, y_end, depth = edge_notch
        if side not in {"left", "right"}:
            raise ValueError("edge notch side must be left or right")
        if not 0 <= y_start < y_end <= height or depth <= 0 or depth >= belt_width:
            raise ValueError("edge notch geometry is invalid")
        if side == "left":
            image[y_start:y_end, left : left + depth] = background
        else:
            right = left + belt_width
            image[y_start:y_end, right - depth : right] = background

    if impulse_noise_fraction:
        rng = np.random.default_rng(seed)
        count = int(round(width * height * impulse_noise_fraction))
        if count:
            ys = rng.integers(0, height, size=count)
            xs = rng.integers(0, width, size=count)
            values = rng.choice(np.array([0.0, 255.0], dtype=np.float32), size=count)
            image[ys, xs] = values

    image = np.clip(image, 0, 255).astype(np.uint8)
    return GeneratedBeltFixture(
        image=image,
        expected_left_x=left,
        expected_right_x_exclusive=left + belt_width,
        label=label,
    )
