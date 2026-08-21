"""Statistical testing and multiple-testing correction."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class HypothesisTest:
    test_id: str
    family: str
    p_value: float
    effect_size: float
    n_observations: int
    raw_p_value: float
    adjusted_p_value: float = 0.0
    significant: bool = False
    ci_lower: float = 0.0
    ci_upper: float = 0.0


def benjamini_hochberg(
    tests: list[HypothesisTest],
    alpha: float = 0.05,
) -> list[HypothesisTest]:
    if not tests:
        return tests
    sorted_tests = sorted(tests, key=lambda t: t.p_value)
    m = len(sorted_tests)
    for i, test in enumerate(sorted_tests):
        adjusted = test.p_value * m / (i + 1)
        adjusted = min(adjusted, 1.0)
        test.adjusted_p_value = adjusted
        test.significant = adjusted <= alpha
    for orig, sorted_t in zip(tests, sorted_tests):
        orig.adjusted_p_value = sorted_t.adjusted_p_value
        orig.significant = sorted_t.significant
    return tests


def compute_confidence_interval(
    effect_size: float,
    n: int,
    confidence: float = 0.95,
) -> tuple[float, float]:
    if n <= 1:
        return (effect_size, effect_size)
    se = math.sqrt(effect_size * (1 - effect_size) / n)
    z = 1.96 if confidence == 0.95 else 1.645
    return (effect_size - z * se, effect_size + z * se)


def proportion_z_test(
    successes: int,
    n: int,
    p0: float = 0.5,
) -> float:
    if n == 0:
        return 1.0
    p_hat = successes / n
    se = math.sqrt(p0 * (1 - p0) / n)
    if se == 0:
        return 1.0
    z = (p_hat - p0) / se
    p_value = math.erfc(abs(z) / math.sqrt(2))
    return min(p_value, 1.0)


def cohens_h(p1: float, p2: float) -> float:
    return 2 * math.asin(math.sqrt(p1)) - 2 * math.asin(math.sqrt(p2))
