"""Preprocessing: fit on training data only, apply to all."""

from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class StandardScaler:
    means: list[float] | None = None
    stds: list[float] | None = None
    _fitted: bool = False

    def fit(self, X: list[list[float]]) -> None:
        n_features = len(X[0]) if X else 0
        n = len(X)
        self.means = [0.0] * n_features
        self.stds = [0.0] * n_features
        for j in range(n_features):
            vals = [X[i][j] for i in range(n)]
            self.means[j] = sum(vals) / n
            var = sum((v - self.means[j]) ** 2 for v in vals) / max(n - 1, 1)
            self.stds[j] = var ** 0.5
        self._fitted = True

    def transform(self, X: list[list[float]]) -> list[list[float]]:
        if not self._fitted or self.means is None or self.stds is None:
            return X
        result = []
        for row in X:
            new_row = []
            for j in range(min(len(row), len(self.means))):
                if self.stds[j] > 1e-10:
                    new_row.append((row[j] - self.means[j]) / self.stds[j])
                else:
                    new_row.append(row[j] - self.means[j])
            result.append(new_row)
        return result

    def fit_transform(self, X: list[list[float]]) -> list[list[float]]:
        self.fit(X)
        return self.transform(X)


def impute_missing(X: list[list[float]], fill_value: float = 0.0) -> list[list[float]]:
    result = []
    for row in X:
        new_row = []
        for v in row:
            if v is None or (isinstance(v, float) and (math.isnan(v) or math.isinf(v))):
                new_row.append(fill_value)
            else:
                new_row.append(v)
        result.append(new_row)
    return result


def temporal_feature_matrix(
    feature_arrays: dict[str, list[float | None]],
    valid_mask: list[bool],
) -> tuple[list[list[float]], list[int]]:
    feature_ids = sorted(feature_arrays.keys())
    X = []
    indices = []
    for i in range(len(valid_mask)):
        if not valid_mask[i]:
            continue
        row = []
        valid = True
        for fid in feature_ids:
            val = feature_arrays[fid][i]
            if val is None:
                valid = False
                break
            row.append(val)
        if valid:
            X.append(row)
            indices.append(i)
    return X, indices
