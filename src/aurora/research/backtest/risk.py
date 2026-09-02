from __future__ import annotations

from dataclasses import dataclass
from math import sqrt


@dataclass(frozen=True)
class RiskMetrics:
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    max_drawdown_recovery: int = 0
    value_at_risk_95: float = 0.0
    conditional_var_95: float = 0.0
    volatility_annualized: float = 0.0
    tail_ratio: float = 0.0
    ulcer_index: float = 0.0
    pain_index: float = 0.0


def compute_risk_metrics(
    equity_curve: list[float],
    periods_per_year: int = 252,
    confidence: float = 0.95,
) -> RiskMetrics:
    if not equity_curve or len(equity_curve) < 2:
        return RiskMetrics()

    returns = []
    for i in range(1, len(equity_curve)):
        if equity_curve[i - 1] > 0:
            returns.append(
                (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
            )
        else:
            returns.append(0.0)

    mean_ret = sum(returns) / len(returns) if returns else 0.0
    variance = (
        sum((r - mean_ret) ** 2 for r in returns) / (len(returns) - 1)
        if len(returns) > 1
        else 0.0
    )
    vol = sqrt(variance) if variance > 0 else 0.0
    ann_vol = vol * sqrt(periods_per_year)

    sorted_returns = sorted(returns)
    idx = int(len(sorted_returns) * (1 - confidence))
    idx = max(0, min(idx, len(sorted_returns) - 1))
    var_95 = sorted_returns[idx]

    tail = sorted_returns[: idx + 1]
    cvar_95 = sum(tail) / len(tail) if tail else 0.0

    p95 = sorted_returns[int(len(sorted_returns) * 0.95)] if sorted_returns else 0.0
    p05 = sorted_returns[int(len(sorted_returns) * 0.05)] if sorted_returns else 0.0
    tail_ratio = abs(p95 / p05) if p05 != 0 else 0.0

    peak = equity_curve[0]
    drawdowns = []
    max_dd = 0.0
    max_dd_duration = 0
    current_dd_duration = 0
    dd_recovery = 0
    recovery_found = False
    for val in equity_curve:
        if val >= peak:
            peak = val
            current_dd_duration = 0
            if not recovery_found and len(drawdowns) > 0:
                dd_recovery += 1
                recovery_found = True
        else:
            dd = (peak - val) / peak if peak > 0 else 0.0
            drawdowns.append(dd)
            current_dd_duration += 1
            recovery_found = False
            if dd > max_dd:
                max_dd = dd
            if current_dd_duration > max_dd_duration:
                max_dd_duration = current_dd_duration

    ulcer = sqrt(sum(d**2 for d in drawdowns) / len(drawdowns)) if drawdowns else 0.0
    pain = sum(drawdowns) / len(drawdowns) if drawdowns else 0.0

    return RiskMetrics(
        max_drawdown=max_dd,
        max_drawdown_duration=max_dd_duration,
        max_drawdown_recovery=dd_recovery,
        value_at_risk_95=var_95,
        conditional_var_95=cvar_95,
        volatility_annualized=ann_vol,
        tail_ratio=tail_ratio,
        ulcer_index=ulcer,
        pain_index=pain,
    )
