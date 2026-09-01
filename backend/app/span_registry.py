"""Configured registry for BeltWatch belt-span estimators.

The registry keeps algorithm selection explicit and fail-closed. Optional providers
are imported lazily so the core FastAPI backend does not require CV dependencies.
"""

from dataclasses import dataclass
from typing import Callable

from .edge_span import DarkScanlineEstimator, MultiRowDarkEstimator, SpanEstimator


class SpanProviderConfigurationError(ValueError):
    pass


@dataclass(frozen=True)
class SpanProviderInfo:
    name: str
    family: str
    requires_optional_cv: bool
    validation_stage: str


ProviderFactory = Callable[[], SpanEstimator]


def _opencv_factory() -> SpanEstimator:
    try:
        from .opencv_span import OpenCVContourEstimator
        return OpenCVContourEstimator()
    except ImportError as exc:
        raise SpanProviderConfigurationError(
            "opencv-contour requires backend/requirements-cv.txt"
        ) from exc


_PROVIDER_INFO = {
    "scanline": SpanProviderInfo("scanline", "classical-cv", False, "development-baseline"),
    "multirow": SpanProviderInfo("multirow", "classical-cv", False, "synthetic-robustness"),
    "opencv-contour": SpanProviderInfo("opencv-contour", "classical-cv", True, "synthetic-robustness"),
}

_PROVIDER_FACTORIES: dict[str, ProviderFactory] = {
    "scanline": lambda: DarkScanlineEstimator(),
    "multirow": lambda: MultiRowDarkEstimator(),
    "opencv-contour": _opencv_factory,
}


def available_span_providers() -> tuple[SpanProviderInfo, ...]:
    return tuple(_PROVIDER_INFO[name] for name in sorted(_PROVIDER_INFO))


def build_span_estimator(name: str) -> SpanEstimator:
    selected = name.strip().lower()
    if not selected:
        raise SpanProviderConfigurationError("span provider name must not be empty")
    try:
        factory = _PROVIDER_FACTORIES[selected]
    except KeyError as exc:
        choices = ", ".join(sorted(_PROVIDER_FACTORIES))
        raise SpanProviderConfigurationError(
            f"unknown span provider {selected!r}; available providers: {choices}"
        ) from exc
    return factory()
