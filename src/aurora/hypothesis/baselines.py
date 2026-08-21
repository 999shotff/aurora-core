from __future__ import annotations

import random as _random
from dataclasses import dataclass
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

BaselineType = Literal[
    "majority_class", "random", "buy_and_hold", "logistic_regression", "simple_tree"
]


class BaselinePrediction(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    model_id: str
    baseline_type: BaselineType
    predictions: list[float]
    probabilities: list[float] = Field(default_factory=list)
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)


@dataclass(frozen=True)
class BaselineModel:
    baseline_type: BaselineType
    model_id: str = ""
    seed: int = 42

    def __post_init__(self) -> None:
        if not self.model_id:
            object.__setattr__(self, "model_id", f"baseline_{self.baseline_type}")

    def predict(self, features: list[list[float]], targets: list[float] | None = None) -> BaselinePrediction:
        if self.baseline_type == "majority_class":
            return self._majority_class(targets)
        elif self.baseline_type == "random":
            return self._random_predict(len(features))
        elif self.baseline_type == "buy_and_hold":
            return self._buy_and_hold(len(features))
        elif self.baseline_type == "logistic_regression":
            return self._logistic_regression(features, targets)
        elif self.baseline_type == "simple_tree":
            return self._simple_tree(features, targets)
        raise ValueError(f"Unknown baseline type: {self.baseline_type}")

    def _majority_class(self, targets: list[float] | None) -> BaselinePrediction:
        if not targets:
            pred = 0.0
        else:
            pos = sum(1 for t in targets if t > 0)
            neg = sum(1 for t in targets if t < 0)
            pred = 1.0 if pos >= neg else -1.0
        predictions = [pred]
        return BaselinePrediction(
            model_id=self.model_id,
            baseline_type=self.baseline_type,
            predictions=predictions,
            probabilities=[0.5],
        )

    def _random_predict(self, n: int) -> BaselinePrediction:
        rng = _random.Random(self.seed)
        predictions = [rng.choice([-1.0, 0.0, 1.0]) for _ in range(n)]
        probabilities = [abs(p) * 0.5 + 0.25 for p in predictions]
        return BaselinePrediction(
            model_id=self.model_id,
            baseline_type=self.baseline_type,
            predictions=predictions,
            probabilities=probabilities,
        )

    def _buy_and_hold(self, n: int) -> BaselinePrediction:
        return BaselinePrediction(
            model_id=self.model_id,
            baseline_type=self.baseline_type,
            predictions=[1.0] * n,
            probabilities=[0.5] * n,
            metadata={"strategy": "always_long"},
        )

    def _logistic_regression(
        self, features: list[list[float]], targets: list[float] | None
    ) -> BaselinePrediction:
        if not features or not targets or len(features) != len(targets):
            return self._random_predict(len(features))
        n_features = len(features[0]) if features else 0
        weights = [0.0] * n_features
        bias = 0.0
        lr = 0.01
        for _ in range(100):
            for x, y in zip(features, targets):
                z = sum(w * xi for w, xi in zip(weights, x)) + bias
                pred = 1.0 / (1.0 + max(min(-z, 500), -500))
                target = 1.0 if y > 0 else 0.0
                error = pred - target
                weights = [w - lr * error * xi for w, xi in zip(weights, x)]
                bias -= lr * error
        predictions = []
        probabilities = []
        for x in features:
            z = sum(w * xi for w, xi in zip(weights, x)) + bias
            prob = 1.0 / (1.0 + max(min(-z, 500), -500))
            pred = 1.0 if prob > 0.5 else -1.0
            predictions.append(pred)
            probabilities.append(prob)
        return BaselinePrediction(
            model_id=self.model_id,
            baseline_type=self.baseline_type,
            predictions=predictions,
            probabilities=probabilities,
            metadata={"n_features": n_features, "n_iterations": 100},
        )

    def _simple_tree(
        self, features: list[list[float]], targets: list[float] | None
    ) -> BaselinePrediction:
        if not features or not targets or len(features) != len(targets):
            return self._random_predict(len(features))
        best_feature = 0
        best_threshold = 0.0
        best_score = -1.0
        for j in range(len(features[0])):
            vals = sorted({x[j] for x in features})
            for t_idx in range(0, len(vals), max(1, len(vals) // 10)):
                threshold = vals[t_idx]
                left_targets = [t for x, t in zip(features, targets) if x[j] <= threshold]
                right_targets = [t for x, t in zip(features, targets) if x[j] > threshold]
                if not left_targets or not right_targets:
                    continue
                left_pos = sum(1 for t in left_targets if t > 0) / len(left_targets)
                right_pos = sum(1 for t in right_targets if t > 0) / len(right_targets)
                score = abs(left_pos - right_pos)
                if score > best_score:
                    best_score = score
                    best_feature = j
                    best_threshold = threshold
        predictions = []
        probabilities = []
        for x in features:
            if x[best_feature] <= best_threshold:
                left_targets = [t for xi, t in zip(features, targets) if xi[best_feature] <= best_threshold]
                prob = sum(1 for t in left_targets if t > 0) / len(left_targets) if left_targets else 0.5
            else:
                right_targets = [t for xi, t in zip(features, targets) if xi[best_feature] > best_threshold]
                prob = sum(1 for t in right_targets if t > 0) / len(right_targets) if right_targets else 0.5
            pred = 1.0 if prob > 0.5 else -1.0
            predictions.append(pred)
            probabilities.append(prob)
        return BaselinePrediction(
            model_id=self.model_id,
            baseline_type=self.baseline_type,
            predictions=predictions,
            probabilities=probabilities,
            metadata={
                "best_feature": best_feature,
                "best_threshold": best_threshold,
                "best_score": best_score,
            },
        )


def create_all_baselines(seed: int = 42) -> list[BaselineModel]:
    return [
        BaselineModel(baseline_type="majority_class", seed=seed),
        BaselineModel(baseline_type="random", seed=seed),
        BaselineModel(baseline_type="buy_and_hold", seed=seed),
        BaselineModel(baseline_type="logistic_regression", seed=seed),
        BaselineModel(baseline_type="simple_tree", seed=seed),
    ]
