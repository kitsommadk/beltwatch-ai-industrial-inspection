import pytest

from app.edge_span import DarkScanlineEstimator, MultiRowDarkEstimator
from app.span_registry import (
    SpanProviderConfigurationError,
    available_span_providers,
    build_span_estimator,
)


def test_registry_lists_explicit_provider_metadata():
    providers = {provider.name: provider for provider in available_span_providers()}

    assert set(providers) == {"scanline", "multirow", "opencv-contour"}
    assert providers["multirow"].validation_stage == "synthetic-robustness"
    assert providers["opencv-contour"].requires_optional_cv is True


def test_core_providers_build_without_optional_cv_dependencies():
    assert isinstance(build_span_estimator("scanline"), DarkScanlineEstimator)
    assert isinstance(build_span_estimator("MULTIROW"), MultiRowDarkEstimator)


def test_unknown_provider_fails_closed():
    with pytest.raises(SpanProviderConfigurationError, match="unknown span provider"):
        build_span_estimator("magic-model")


def test_empty_provider_name_fails_closed():
    with pytest.raises(SpanProviderConfigurationError, match="must not be empty"):
        build_span_estimator("   ")
