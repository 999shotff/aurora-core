"""Methodology scorecard generator."""

from __future__ import annotations

from dataclasses import dataclass

from aurora.benchmark.preregistration import PreRegistrationLog
from aurora.benchmark.registry import CandidateRegistry
from aurora.benchmark.runner import ExperimentResult


@dataclass
class ScorecardRow:
    methodology: str
    hypothesis: str
    sample_size: int
    baseline_da: float
    strategy_da: float
    cost_adjusted_return: float
    robustness_score: float
    leakage_pass: bool
    classification: str


def generate_scorecard(
    results: list[ExperimentResult],
    prereg_log: PreRegistrationLog,
    registry: CandidateRegistry,
) -> list[ScorecardRow]:
    rows: list[ScorecardRow] = []
    for r in results:
        prereg = prereg_log.get(r.experiment_id)
        leakage_pass = all(r.leakage_checks.values()) if r.leakage_checks else False
        robustness_count = len([v for v in r.robustness.values() if v > 0.5])
        robustness_total = max(len(r.robustness), 1)
        robustness_score = robustness_count / robustness_total
        rows.append(ScorecardRow(
            methodology=r.methodology,
            hypothesis=prereg.hypothesis_text if prereg else "",
            sample_size=r.test_size,
            baseline_da=r.baseline_da,
            strategy_da=r.strategy_da,
            cost_adjusted_return=r.cost_adjusted_mean_return,
            robustness_score=robustness_score,
            leakage_pass=leakage_pass,
            classification=r.classification,
        ))
    return rows


def format_scorecard(rows: list[ScorecardRow]) -> str:
    lines = [
        "=" * 100,
        "METHODOLOGY SCORECARD",
        "=" * 100,
        f"{'Methodology':<22} {'DA':>6} {'Base':>6} {'CA Ret':>10} {'Robust':>7} {'Leak':>5} {'Class':<14}",
        "-" * 100,
    ]
    for row in rows:
        lines.append(
            f"{row.methodology:<22} {row.strategy_da:>6.4f} {row.baseline_da:>6.4f} "
            f"{row.cost_adjusted_return:>10.6f} {row.robustness_score:>7.2f} "
            f"{'Y' if row.leakage_pass else 'N':>5} {row.classification:<14}"
        )
    lines.append("=" * 100)
    return "\n".join(lines)


def format_methodology_summary(
    results: list[ExperimentResult],
    prereg_log: PreRegistrationLog,
) -> str:
    lines = ["", "DETAILED METHODOLOGY RESULTS", "-" * 80]
    for r in results:
        prereg = prereg_log.get(r.experiment_id)
        lines.append(f"\n--- {r.methodology.upper()} ({r.experiment_id}) ---")
        lines.append(f"Hypothesis: {prereg.hypothesis_text if prereg else 'N/A'}")
        lines.append(f"Source: {prereg.source_document if prereg else 'N/A'} p.{prereg.source_page if prereg else 0}")
        lines.append(f"Dataset: {r.dataset_instrument}")
        lines.append(f"Train: {r.train_size} | Val: {r.val_size} | Test: {r.test_size}")
        lines.append(f"Signals: {r.signal_count}")
        lines.append(f"Strategy DA: {r.strategy_da:.4f} | Baseline DA: {r.baseline_da:.4f}")
        lines.append(f"Strategy Mean: {r.strategy_mean_return:.6f} | Baseline Mean: {r.baseline_mean_return:.6f}")
        lines.append(f"Strategy Sharpe: {r.strategy_sharpe:.4f} | Baseline Sharpe: {r.baseline_sharpe:.4f}")
        lines.append(f"Max DD: {r.strategy_max_drawdown:.4f} | Baseline Max DD: {r.baseline_max_drawdown:.4f}")
        lines.append(f"Brier: {r.strategy_brier:.4f} | Baseline Brier: 0.2500")
        lines.append(f"Cost-Adjusted Mean: {r.cost_adjusted_mean_return:.6f}")
        lines.append(f"Cost-Adjusted Sharpe: {r.cost_adjusted_sharpe:.4f}")
        lines.append(f"Classification: {r.classification}")
        lines.append(f"Leakage: {r.leakage_checks}")
        if r.robustness:
            lines.append(f"Robustness ({len(r.robustness)} variations):")
            for k, v in sorted(r.robustness.items()):
                lines.append(f"  {k}: {v:.4f}")
        lines.append(f"Negative Control DA: {r.negative_control_da:.4f}")
    return "\n".join(lines)
