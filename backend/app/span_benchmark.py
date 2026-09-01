"""Deterministic benchmark helpers for BeltWatch edge-span estimators.

The benchmark operates on generated/replay fixtures with known ground-truth pixel
geometry. It measures algorithm error only; it does not validate physical camera
calibration or production metrology.
"""

from dataclasses import dataclass
from statistics import mean
from time import perf_counter
from typing import Iterable

from .camera import FramePacket
from .edge_span import SpanEstimator


@dataclass(frozen=True)
class SpanBenchmarkCase:
    name: str
    frame: FramePacket
    expected_left_x: int
    expected_right_x_exclusive: int

    @property
    def expected_span_px(self) -> int:
        return self.expected_right_x_exclusive - self.expected_left_x


@dataclass(frozen=True)
class SpanBenchmarkResult:
    cases: int
    successes: int
    failures: int
    exact_matches: int
    mean_absolute_span_error_px: float | None
    max_absolute_span_error_px: int | None
    mean_edge_error_px: float | None
    mean_latency_ms: float

    @property
    def success_rate(self) -> float:
        return self.successes / self.cases if self.cases else 0.0

    @property
    def exact_match_rate(self) -> float:
        return self.exact_matches / self.cases if self.cases else 0.0


def benchmark_span_estimator(
    estimator: SpanEstimator,
    cases: Iterable[SpanBenchmarkCase],
) -> SpanBenchmarkResult:
    case_list = list(cases)
    span_errors: list[int] = []
    edge_errors: list[float] = []
    latencies_ms: list[float] = []
    successes = 0
    exact_matches = 0

    for case in case_list:
        started = perf_counter()
        try:
            span = estimator.estimate(case.frame)
        except ValueError:
            latencies_ms.append((perf_counter() - started) * 1000)
            continue
        latencies_ms.append((perf_counter() - started) * 1000)
        successes += 1

        span_error = abs(span.span_px - case.expected_span_px)
        left_error = abs(span.left_x - case.expected_left_x)
        right_error = abs(span.right_x_exclusive - case.expected_right_x_exclusive)
        span_errors.append(span_error)
        edge_errors.append((left_error + right_error) / 2)
        if span_error == 0 and left_error == 0 and right_error == 0:
            exact_matches += 1

    return SpanBenchmarkResult(
        cases=len(case_list),
        successes=successes,
        failures=len(case_list) - successes,
        exact_matches=exact_matches,
        mean_absolute_span_error_px=mean(span_errors) if span_errors else None,
        max_absolute_span_error_px=max(span_errors) if span_errors else None,
        mean_edge_error_px=mean(edge_errors) if edge_errors else None,
        mean_latency_ms=mean(latencies_ms) if latencies_ms else 0.0,
    )
