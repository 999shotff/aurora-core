from __future__ import annotations

from collections import Counter
from collections.abc import Sequence


def brier_score(probability: float, actual_positive: bool) -> float:
    if not 0.0 <= probability <= 1.0:
        raise ValueError("probability must be between 0 and 1")
    target = 1.0 if actual_positive else 0.0
    return (probability - target) ** 2


def mean_brier_score(records: list[tuple[float, bool]]) -> float:
    if not records:
        return 0.0
    return sum(brier_score(p, a) for p, a in records) / len(records)


def directional_accuracy(predicted: str, actual: str) -> bool | None:
    if predicted in ("unknown", "abstain") or actual in ("unknown", "abstain"):
        return None
    return predicted == actual


def calibration_error(
    predictions: list[tuple[float, bool]], n_bins: int = 10
) -> float:
    if not predictions:
        return 0.0

    bins: dict[int, list[tuple[float, bool]]] = {}
    for prob, actual in predictions:
        bin_idx = min(int(prob * n_bins), n_bins - 1)
        bins.setdefault(bin_idx, []).append((prob, actual))

    total_error = 0.0
    total_count = 0
    for bin_idx, items in bins.items():
        bin_start = bin_idx / n_bins
        bin_end = (bin_idx + 1) / n_bins
        expected_prob = (bin_start + bin_end) / 2.0
        actual_positive_rate = sum(1 for _, a in items if a) / len(items)
        bin_error = abs(expected_prob - actual_positive_rate)
        total_error += bin_error * len(items)
        total_count += len(items)

    return total_error / total_count if total_count > 0 else 0.0


def abstention_quality(
    abstained: list[bool], correct: list[bool | None]
) -> dict[str, float]:
    if not abstained:
        return {"abstention_rate": 0.0, "non_abstain_accuracy": 0.0}

    n_abstained = sum(abstained)
    abstention_rate = n_abstained / len(abstained)

    non_abstain_correct = [
        c for a, c in zip(abstained, correct) if not a and c is not None
    ]
    non_abstain_accuracy = (
        sum(non_abstain_correct) / len(non_abstain_correct)
        if non_abstain_correct
        else 0.0
    )

    return {
        "abstention_rate": abstention_rate,
        "non_abstain_accuracy": non_abstain_accuracy,
    }


def outcome_distribution(outcomes: Sequence[str]) -> dict[str, int]:
    return dict(Counter(outcomes))

