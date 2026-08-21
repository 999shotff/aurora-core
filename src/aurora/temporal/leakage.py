from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

LeakageType = Literal[
    "future_price_leakage",
    "future_volume_leakage",
    "future_derived_indicator",
    "random_temporal_split",
    "normalization_on_test",
    "target_leakage",
    "overlapping_horizons",
    "feature_timestamp_violation",
]


class LeakageCheck(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    leakage_type: LeakageType
    passed: bool
    details: str = ""
    severity: Literal["critical", "warning", "info"] = "critical"


class LeakageDetector:
    def __init__(self) -> None:
        self.checks: list[LeakageCheck] = []

    def add_check(self, check: LeakageCheck) -> None:
        self.checks.append(check)

    def all_passed(self) -> bool:
        return all(c.passed for c in self.checks if c.severity == "critical")

    def critical_failures(self) -> list[LeakageCheck]:
        return [c for c in self.checks if not c.passed and c.severity == "critical"]

    def summary(self) -> dict[str, int]:
        passed = sum(1 for c in self.checks if c.passed)
        failed = sum(1 for c in self.checks if not c.passed)
        return {"total": len(self.checks), "passed": passed, "failed": failed}

    def reset(self) -> None:
        self.checks.clear()


def check_feature_timestamp_leakage(
    feature_timestamps: list[datetime], prediction_timestamps: list[datetime]
) -> LeakageCheck:
    violations = 0
    for ft, pt in zip(feature_timestamps, prediction_timestamps):
        if ft > pt:
            violations += 1
    passed = violations == 0
    return LeakageCheck(
        leakage_type="feature_timestamp_violation",
        passed=passed,
        details=f"{violations} feature(s) have timestamp after prediction timestamp",
        severity="critical",
    )


def check_normalization_leakage(
    train_stats: dict[str, float],
    test_stats: dict[str, float],
    tolerance: float = 0.1,
) -> LeakageCheck:
    mismatches = 0
    for key, train_val in train_stats.items():
        if key in test_stats:
            test_val = test_stats[key]
            if train_val != 0.0:
                diff = abs(train_val - test_val) / abs(train_val)
                if diff > tolerance:
                    mismatches += 1
    passed = mismatches == 0
    return LeakageCheck(
        leakage_type="normalization_on_test",
        passed=passed,
        details=f"{mismatches} feature(s) have train/test stat mismatch > {tolerance}",
        severity="critical",
    )


def check_random_temporal_split(
    train_timestamps: list[datetime], test_timestamps: list[datetime]
) -> LeakageCheck:
    if not train_timestamps or not test_timestamps:
        return LeakageCheck(
            leakage_type="random_temporal_split",
            passed=True,
            details="Empty splits, skipping check",
            severity="info",
        )
    max_train = max(train_timestamps)
    overlaps = sum(1 for t in test_timestamps if t <= max_train)
    passes_sorted = all(
        train_timestamps[i] <= train_timestamps[i + 1]
        for i in range(len(train_timestamps) - 1)
    )
    passed = overlaps == 0 and passes_sorted
    return LeakageCheck(
        leakage_type="random_temporal_split",
        passed=passed,
        details=f"{overlaps} test timestamps <= max train timestamp; sorted={passes_sorted}",
        severity="critical",
    )


def check_target_leakage(
    feature_timestamps: list[datetime],
    target_end_timestamps: list[datetime],
) -> LeakageCheck:
    violations = 0
    for ft, te in zip(feature_timestamps, target_end_timestamps):
        if te <= ft:
            violations += 1
    passed = violations == 0
    return LeakageCheck(
        leakage_type="target_leakage",
        passed=passed,
        details=f"{violations} targets end before or at feature timestamp",
        severity="critical",
    )


def check_overlapping_horizons(
    windows: list[tuple[datetime, datetime]],
) -> LeakageCheck:
    overlaps = 0
    sorted_windows = sorted(windows, key=lambda w: w[0])
    for i in range(len(sorted_windows) - 1):
        if sorted_windows[i][1] > sorted_windows[i + 1][0]:
            overlaps += 1
    passed = overlaps == 0
    return LeakageCheck(
        leakage_type="overlapping_horizons",
        passed=passed,
        details=f"{overlaps} overlapping window boundaries detected",
        severity="critical",
    )
