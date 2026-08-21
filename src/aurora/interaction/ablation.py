"""Walk-forward validation and ablation framework."""

from __future__ import annotations

from dataclasses import dataclass

from aurora.interaction.models import BaggedEnsemble, DecisionTreeModel, LogisticRegressionModel
from aurora.interaction.preprocessing import StandardScaler, impute_missing


@dataclass
class EvalMetrics:
    directional_accuracy: float = 0.0
    balanced_accuracy: float = 0.0
    majority_class_accuracy: float = 0.0
    class_distribution: tuple[int, int] = (0, 0)
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0
    brier_score: float = 0.0
    calibration_error: float = 0.0
    mean_return: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown: float = 0.0
    n_observations: int = 0
    n_trades: int = 0

    def to_dict(self) -> dict[str, float]:
        return {
            "directional_accuracy": self.directional_accuracy,
            "balanced_accuracy": self.balanced_accuracy,
            "majority_class_accuracy": self.majority_class_accuracy,
            "class_positive": float(self.class_distribution[0]),
            "class_negative": float(self.class_distribution[1]),
            "precision": self.precision,
            "recall": self.recall,
            "f1": self.f1,
            "brier_score": self.brier_score,
            "calibration_error": self.calibration_error,
            "mean_return": self.mean_return,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "n_observations": float(self.n_observations),
            "n_trades": float(self.n_trades),
        }


def compute_metrics(
    y_true: list[float],
    y_pred: list[float],
    y_proba: list[float],
    returns: list[float] | None = None,
) -> EvalMetrics:
    n = len(y_true)
    if n == 0:
        return EvalMetrics()
    correct = sum(1 for t, p in zip(y_true, y_pred) if t == p)
    da = correct / n
    tp = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 1)
    fp = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 1)
    fn = sum(1 for t, p in zip(y_true, y_pred) if t == 1 and p == 0)
    tn = sum(1 for t, p in zip(y_true, y_pred) if t == 0 and p == 0)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0.0
    ba = 0.0
    if (tp + fn) > 0 and (tn + fp) > 0:
        ba = 0.5 * (tp / (tp + fn) + tn / (tn + fp))
    n_pos = sum(1 for t in y_true if t == 1.0)
    n_neg = sum(1 for t in y_true if t == 0.0)
    majority_class_da = max(n_pos, n_neg) / n
    brier = sum((p - t) ** 2 for t, p in zip(y_true, y_proba)) / n
    bins: dict[int, list[tuple[float, float]]] = {}
    for p, t in zip(y_proba, y_true):
        b = min(int(p * 10), 9)
        bins.setdefault(b, []).append((p, t))
    cal_err = 0.0
    for items in bins.values():
        expected = sum(p for p, _ in items) / len(items)
        actual = sum(t for _, t in items) / len(items)
        cal_err += abs(expected - actual) * len(items)
    cal_err /= n
    mean_ret = 0.0
    sharpe = 0.0
    mdd = 0.0
    n_trades = 0
    if returns:
        n_trades = sum(1 for r in returns if r != 0.0)
        mean_ret = sum(returns) / len(returns)
        if len(returns) > 1:
            var = sum((r - mean_ret) ** 2 for r in returns) / (len(returns) - 1)
            std = var ** 0.5
            sharpe = mean_ret / std if std > 0 else 0.0
        cum = 1.0
        peak = 1.0
        for r in returns:
            cum *= 1 + r
            peak = max(peak, cum)
            dd = (peak - cum) / peak if peak > 0 else 0.0
            mdd = max(mdd, dd)
    return EvalMetrics(
        directional_accuracy=da,
        balanced_accuracy=ba,
        majority_class_accuracy=majority_class_da,
        class_distribution=(n_pos, n_neg),
        precision=precision,
        recall=recall,
        f1=f1,
        brier_score=brier,
        calibration_error=cal_err,
        mean_return=mean_ret,
        sharpe_ratio=sharpe,
        max_drawdown=mdd,
        n_observations=n,
        n_trades=n_trades,
    )


def _create_model(model_type: str) -> LogisticRegressionModel | DecisionTreeModel | BaggedEnsemble:
    if model_type == "ensemble":
        return BaggedEnsemble(n_trees=10, max_depth=3, subsample_ratio=0.8)
    elif model_type == "tree":
        return DecisionTreeModel(max_depth=4, min_samples_split=10)
    else:
        return LogisticRegressionModel(learning_rate=0.01, n_iterations=300, l2_penalty=0.001)


@dataclass
class AblationResult:
    experiment_id: str
    feature_groups: list[str]
    model_type: str
    train_size: int
    test_size: int
    metrics: EvalMetrics
    negative_control_da: float
    feature_importances: list[float]
    feature_names: list[str]


def walk_forward_evaluate(
    X: list[list[float]],
    y: list[float],
    feature_names: list[str],
    model_type: str = "logistic",
    n_folds: int = 3,
    min_train: int = 100,
    transaction_cost_bps: float = 10.0,
    seed: int = 42,
) -> tuple[EvalMetrics, list[float]]:
    n = len(X)
    if n < min_train + 50:
        return EvalMetrics(), [0.0] * len(feature_names)
    fold_size = (n - min_train) // n_folds
    all_metrics: list[EvalMetrics] = []
    all_returns: list[float] = []
    last_train_end = 0
    for fold in range(n_folds):
        train_end = min_train + fold * fold_size
        test_end = min(train_end + fold_size, n)
        if test_end <= train_end:
            break
        train_X = X[:train_end]
        train_y = y[:train_end]
        test_X = X[train_end:test_end]
        test_y = y[train_end:test_end]
        scaler = StandardScaler()
        train_X_s = scaler.fit_transform(impute_missing(train_X))
        test_X_s = scaler.transform(impute_missing(test_X))
        model = _create_model(model_type)
        if isinstance(model, BaggedEnsemble):
            model.fit(train_X_s, train_y, seed=seed)
        else:
            model.fit(train_X_s, train_y)
        y_proba = model.predict_proba(test_X_s)
        y_pred = [1.0 if p >= 0.5 else 0.0 for p in y_proba]
        strategy_returns = []
        cost = transaction_cost_bps / 10000.0
        prev_pred = 0.0
        for pred, actual in zip(y_pred, test_y):
            r = (1.0 if actual == 1.0 else -1.0) if pred == 1.0 else 0.0
            if pred != prev_pred:
                r -= cost
            strategy_returns.append(r)
            prev_pred = pred
        metrics = compute_metrics(test_y, y_pred, y_proba, strategy_returns)
        all_metrics.append(metrics)
        all_returns.extend(strategy_returns)
        last_train_end = train_end
    if not all_metrics:
        return EvalMetrics(), [0.0] * len(feature_names)
    total_pos = sum(m.class_distribution[0] for m in all_metrics)
    total_neg = sum(m.class_distribution[1] for m in all_metrics)
    total_n = total_pos + total_neg
    majority_da = max(total_pos, total_neg) / total_n if total_n > 0 else 0.5
    total_correct = sum(int(m.directional_accuracy * m.n_observations) for m in all_metrics)
    overall_da = total_correct / total_n if total_n > 0 else 0.0
    total_tp = sum(int(m.recall * m.class_distribution[0]) for m in all_metrics if m.class_distribution[0] > 0)
    total_fn = sum(m.class_distribution[0] for m in all_metrics) - total_tp
    total_tn = sum(int((1 - m.recall) * m.class_distribution[1]) for m in all_metrics if m.class_distribution[1] > 0)
    total_fp = sum(m.class_distribution[1] for m in all_metrics) - total_tn
    overall_ba = 0.0
    if (total_tp + total_fn) > 0 and (total_tn + total_fp) > 0:
        overall_ba = 0.5 * (total_tp / (total_tp + total_fn) + total_tn / (total_tn + total_fp))
    overall_precision = total_tp / (total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    overall_recall = total_tp / (total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    overall_f1 = 2 * overall_precision * overall_recall / (overall_precision + overall_recall) if (overall_precision + overall_recall) > 0 else 0.0
    overall_brier = sum(m.brier_score * m.n_observations for m in all_metrics) / total_n if total_n > 0 else 0.0
    overall_cal = sum(m.calibration_error * m.n_observations for m in all_metrics) / total_n if total_n > 0 else 0.0
    mean_ret = sum(all_returns) / len(all_returns) if all_returns else 0.0
    sharpe = 0.0
    if len(all_returns) > 1:
        var = sum((r - mean_ret) ** 2 for r in all_returns) / (len(all_returns) - 1)
        std = var ** 0.5
        sharpe = mean_ret / std if std > 0 else 0.0
    mdd = 0.0
    cum = 1.0
    peak = 1.0
    for r in all_returns:
        cum *= 1 + r
        peak = max(peak, cum)
        dd = (peak - cum) / peak if peak > 0 else 0.0
        mdd = max(mdd, dd)
    n_trades = sum(m.n_trades for m in all_metrics)
    avg = EvalMetrics(
        directional_accuracy=overall_da,
        balanced_accuracy=overall_ba,
        majority_class_accuracy=majority_da,
        class_distribution=(total_pos, total_neg),
        precision=overall_precision,
        recall=overall_recall,
        f1=overall_f1,
        brier_score=overall_brier,
        calibration_error=overall_cal,
        mean_return=mean_ret,
        sharpe_ratio=sharpe,
        max_drawdown=mdd,
        n_observations=total_n,
        n_trades=n_trades,
    )
    final_scaler = StandardScaler()
    full_train_X = final_scaler.fit_transform(impute_missing(X[:last_train_end]))
    final_model = _create_model(model_type)
    if isinstance(final_model, BaggedEnsemble):
        final_model.fit(full_train_X, y[:last_train_end], seed=seed)
    else:
        final_model.fit(full_train_X, y[:last_train_end])
    importances = final_model.feature_importance()
    while len(importances) < len(feature_names):
        importances.append(0.0)
    return avg, importances[:len(feature_names)]


def run_ablation(
    feature_arrays: dict[str, list[float | None]],
    targets: list[float],
    valid_mask: list[bool],
    feature_groups: dict[str, list[str]],
    model_type: str = "logistic",
    transaction_cost_bps: float = 10.0,
) -> list[AblationResult]:
    results: list[AblationResult] = []
    base_indices = [i for i in range(len(valid_mask)) if valid_mask[i]]

    for group_name, feature_ids in feature_groups.items():
        X_rows = []
        valid_subset = []
        for idx in base_indices:
            row = []
            ok = True
            for fid in feature_ids:
                val = feature_arrays.get(fid, [None] * len(targets))[idx]
                if val is None:
                    ok = False
                    break
                row.append(val)
            if ok:
                X_rows.append(row)
                valid_subset.append(idx)
        y_subset = [targets[i] for i in valid_subset]
        if len(X_rows) < 150:
            continue
        metrics, importances = walk_forward_evaluate(
            X_rows, y_subset, feature_ids, model_type, n_folds=3,
            min_train=max(50, len(X_rows) // 3), transaction_cost_bps=transaction_cost_bps,
        )
        nc_da = _negative_control_da(y_subset, seed=42)
        results.append(AblationResult(
            experiment_id=f"ablation_{group_name}_{model_type}",
            feature_groups=[group_name],
            model_type=model_type,
            train_size=max(50, len(X_rows) // 3),
            test_size=len(X_rows) - max(50, len(X_rows) // 3),
            metrics=metrics,
            negative_control_da=nc_da,
            feature_importances=importances,
            feature_names=feature_ids,
        ))

    combined_ids = list({fid for ids in feature_groups.values() for fid in ids})
    X_all = []
    valid_all = []
    for idx in base_indices:
        row = []
        ok = True
        for fid in combined_ids:
            val = feature_arrays.get(fid, [None] * len(targets))[idx]
            if val is None:
                ok = False
                break
            row.append(val)
        if ok:
            X_all.append(row)
            valid_all.append(idx)
    y_all = [targets[i] for i in valid_all]
    if len(X_all) >= 150:
        metrics, importances = walk_forward_evaluate(
            X_all, y_all, combined_ids, model_type, n_folds=3,
            min_train=max(50, len(X_all) // 3), transaction_cost_bps=transaction_cost_bps,
        )
        nc_da = _negative_control_da(y_all, seed=42)
        results.append(AblationResult(
            experiment_id=f"ablation_combined_{model_type}",
            feature_groups=["combined"],
            model_type=model_type,
            train_size=max(50, len(X_all) // 3),
            test_size=len(X_all) - max(50, len(X_all) // 3),
            metrics=metrics,
            negative_control_da=nc_da,
            feature_importances=importances,
            feature_names=combined_ids,
        ))
    return results


def _negative_control_da(y: list[float], seed: int) -> float:
    import random
    rng = random.Random(seed)
    n = len(y)
    if n == 0:
        return 0.5
    correct = sum(1 for _ in range(n) if rng.random() < 0.5)
    return correct / n
