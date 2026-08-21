"""Simple ML models implemented from scratch.

No external ML dependencies. All models are CPU-friendly and
interpretable. Implements: logistic regression, decision tree,
and bagged ensemble.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass, field


def _sigmoid(z: float) -> float:
    z = max(-500.0, min(500.0, z))
    return 1.0 / (1.0 + math.exp(-z))


@dataclass
class LogisticRegressionModel:
    weights: list[float] = field(default_factory=list)
    bias: float = 0.0
    learning_rate: float = 0.01
    n_iterations: int = 500
    l2_penalty: float = 0.001
    _fitted: bool = False

    def fit(self, X: list[list[float]], y: list[float]) -> None:
        n_features = len(X[0]) if X else 0
        self.weights = [0.0] * n_features
        self.bias = 0.0
        n = len(X)
        for _ in range(self.n_iterations):
            for i in range(n):
                z = sum(self.weights[j] * X[i][j] for j in range(n_features)) + self.bias
                pred = _sigmoid(z)
                error = pred - y[i]
                for j in range(n_features):
                    grad = error * X[i][j] + self.l2_penalty * self.weights[j]
                    self.weights[j] -= self.learning_rate * grad
                self.bias -= self.learning_rate * error
        self._fitted = True

    def predict_proba(self, X: list[list[float]]) -> list[float]:
        n_features = len(self.weights)
        result = []
        for row in X:
            z = sum(self.weights[j] * row[j] for j in range(min(n_features, len(row)))) + self.bias
            result.append(_sigmoid(z))
        return result

    def predict(self, X: list[list[float]], threshold: float = 0.5) -> list[float]:
        return [1.0 if p >= threshold else 0.0 for p in self.predict_proba(X)]

    def feature_importance(self) -> list[float]:
        return [abs(w) for w in self.weights]


@dataclass
class TreeNode:
    feature_idx: int = -1
    threshold: float = 0.0
    left: TreeNode | None = None
    right: TreeNode | None = None
    prediction: float = 0.0
    is_leaf: bool = True
    n_samples: int = 0


@dataclass
class DecisionTreeModel:
    max_depth: int = 4
    min_samples_split: int = 10
    root: TreeNode | None = None
    _fitted: bool = False
    _n_features: int = 0

    def fit(self, X: list[list[float]], y: list[float]) -> None:
        self._n_features = len(X[0]) if X else 0
        self.root = self._build(X, y, 0)
        self._fitted = True

    def _build(self, X: list[list[float]], y: list[float], depth: int) -> TreeNode:
        node = TreeNode(n_samples=len(y))
        if len(y) == 0:
            node.prediction = 0.5
            return node
        pos = sum(y)
        node.prediction = pos / len(y)
        if depth >= self.max_depth or len(y) < self.min_samples_split or node.prediction in (0.0, 1.0):
            node.is_leaf = True
            return node
        best_gain = -1.0
        best_feat = -1
        best_thresh = 0.0
        parent_impurity = self._gini(y)
        for feat in range(self._n_features):
            values = sorted({X[i][feat] for i in range(len(X))})
            for t in values[1::max(1, len(values) // 10)]:
                left_y = [y[i] for i in range(len(X)) if X[i][feat] <= t]
                right_y = [y[i] for i in range(len(X)) if X[i][feat] > t]
                if not left_y or not right_y:
                    continue
                gain = parent_impurity - (
                    len(left_y) / len(y) * self._gini(left_y)
                    + len(right_y) / len(y) * self._gini(right_y)
                )
                if gain > best_gain:
                    best_gain = gain
                    best_feat = feat
                    best_thresh = t
        if best_feat == -1 or best_gain <= 0:
            node.is_leaf = True
            return node
        node.feature_idx = best_feat
        node.threshold = best_thresh
        node.is_leaf = False
        left_idx = [i for i in range(len(X)) if X[i][best_feat] <= best_thresh]
        right_idx = [i for i in range(len(X)) if X[i][best_feat] > best_thresh]
        node.left = self._build([X[i] for i in left_idx], [y[i] for i in left_idx], depth + 1)
        node.right = self._build([X[i] for i in right_idx], [y[i] for i in right_idx], depth + 1)
        return node

    def _gini(self, y: list[float]) -> float:
        if not y:
            return 0.0
        pos = sum(y) / len(y)
        return 1.0 - pos ** 2 - (1.0 - pos) ** 2

    def predict_proba(self, X: list[list[float]]) -> list[float]:
        return [self._predict_one(row, self.root) for row in X]

    def _predict_one(self, row: list[float], node: TreeNode | None) -> float:
        if node is None or node.is_leaf:
            return node.prediction if node else 0.5
        if row[node.feature_idx] <= node.threshold:
            return self._predict_one(row, node.left)
        return self._predict_one(row, node.right)

    def predict(self, X: list[list[float]], threshold: float = 0.5) -> list[float]:
        return [1.0 if p >= threshold else 0.0 for p in self.predict_proba(X)]

    def feature_importance(self) -> list[float]:
        imp = [0.0] * self._n_features
        if self.root:
            self._count_importance(self.root, imp)
        total = sum(imp) or 1.0
        return [v / total for v in imp]

    def _count_importance(self, node: TreeNode, imp: list[float]) -> float:
        if node.is_leaf or node.left is None or node.right is None:
            return node.n_samples
        left_n = self._count_importance(node.left, imp)
        right_n = self._count_importance(node.right, imp)
        total = left_n + right_n
        if 0 <= node.feature_idx < len(imp):
            imp[node.feature_idx] += total
        return total


@dataclass
class BaggedEnsemble:
    n_trees: int = 10
    max_depth: int = 3
    subsample_ratio: float = 0.8
    trees: list[DecisionTreeModel] = field(default_factory=list)
    _fitted: bool = False

    def fit(self, X: list[list[float]], y: list[float], seed: int = 42) -> None:
        rng = random.Random(seed)
        n = len(X)
        subsample = max(int(n * self.subsample_ratio), 1)
        self.trees = []
        for _ in range(self.n_trees):
            indices = [rng.randint(0, n - 1) for _ in range(subsample)]
            bag_X = [X[i] for i in indices]
            bag_y = [y[i] for i in indices]
            tree = DecisionTreeModel(max_depth=self.max_depth, min_samples_split=5)
            tree.fit(bag_X, bag_y)
            self.trees.append(tree)
        self._fitted = True

    def predict_proba(self, X: list[list[float]]) -> list[float]:
        all_preds = [tree.predict_proba(X) for tree in self.trees]
        n = len(X)
        result = []
        for i in range(n):
            result.append(sum(preds[i] for preds in all_preds) / len(self.trees))
        return result

    def predict(self, X: list[list[float]], threshold: float = 0.5) -> list[float]:
        return [1.0 if p >= threshold else 0.0 for p in self.predict_proba(X)]

    def feature_importance(self) -> list[float]:
        if not self.trees:
            return []
        n_features = self._estimate_n_features()
        if n_features == 0:
            return []
        combined = [0.0] * n_features
        for tree in self.trees:
            imp = tree.feature_importance()
            for j in range(min(len(imp), n_features)):
                combined[j] += imp[j]
        total = sum(combined) or 1.0
        return [v / total for v in combined]

    def _estimate_n_features(self) -> int:
        if not self.trees:
            return 0
        first_tree = self.trees[0]
        return first_tree._n_features
