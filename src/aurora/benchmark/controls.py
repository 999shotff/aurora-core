"""Negative control experiments.

These controls help detect whether the evaluation framework
is discovering false edges from noise or data artifacts.
"""

from __future__ import annotations

import random


def shuffled_signals(
    signals: list[int | None],
    seed: int,
) -> list[int | None]:
    non_none = [(i, s) for i, s in enumerate(signals) if s is not None]
    if not non_none:
        return signals
    vals = [s for _, s in non_none]
    rng = random.Random(seed)
    rng.shuffle(vals)
    result = list(signals)
    for (idx, _), new_val in zip(non_none, vals):
        result[idx] = new_val
    return result


def noise_features(
    n: int,
    seed: int,
) -> list[float]:
    rng = random.Random(seed)
    return [rng.gauss(0.0, 1.0) for _ in range(n)]


def reversed_signals(signals: list[int | None]) -> list[int | None]:
    return [-s if s is not None else None for s in signals]


def random_baseline_da(actual: list[float], seed: int) -> float:
    rng = random.Random(seed)
    correct = 0
    total = 0
    for a in actual:
        if a == 0.0:
            continue
        total += 1
        rand_pred = rng.choice([-1.0, 1.0])
        if (rand_pred > 0 and a > 0) or (rand_pred < 0 and a < 0):
            correct += 1
    return correct / total if total > 0 else 0.0
