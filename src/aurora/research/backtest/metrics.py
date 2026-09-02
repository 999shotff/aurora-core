from __future__ import annotations

from dataclasses import dataclass
from math import sqrt


@dataclass(frozen=True)
class PerformanceMetrics:
    total_return: float = 0.0
    annualized_return: float = 0.0
    sharpe_ratio: float = 0.0
    sortino_ratio: float = 0.0
    max_drawdown: float = 0.0
    max_drawdown_duration: int = 0
    calmar_ratio: float = 0.0
    profit_factor: float = 0.0
    win_rate: float = 0.0
    total_trades: int = 0
    winning_trades: int = 0
    losing_trades: int = 0
    avg_win: float = 0.0
    avg_loss: float = 0.0
    avg_holding_periods: float = 0.0
    total_costs: float = 0.0
    net_pnl: float = 0.0
    gross_profit: float = 0.0
    gross_loss: float = 0.0
    expectancy: float = 0.0
    kelly_fraction: float = 0.0


def _compute_drawdowns(equity_curve: list[float]) -> tuple[list[float], int]:
    if not equity_curve:
        return [], 0
    peak = equity_curve[0]
    drawdowns = []
    max_dd = 0.0
    max_dd_duration = 0
    current_dd_duration = 0
    for val in equity_curve:
        if val >= peak:
            peak = val
            current_dd_duration = 0
        else:
            dd = (peak - val) / peak if peak > 0 else 0.0
            drawdowns.append(dd)
            current_dd_duration += 1
            if dd > max_dd:
                max_dd = dd
            if current_dd_duration > max_dd_duration:
                max_dd_duration = current_dd_duration
        if val < peak:
            drawdowns.append((peak - val) / peak if peak > 0 else 0.0)
    unique_drawdowns = list({round(d, 10) for d in drawdowns})
    unique_drawdowns.sort(reverse=True)
    return unique_drawdowns, max_dd_duration


def compute_metrics(
    equity_curve: list[float],
    trade_pnls: list[float],
    trade_holding_periods: list[int],
    total_costs: float = 0.0,
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252,
) -> PerformanceMetrics:
    if not equity_curve or len(equity_curve) < 2:
        return PerformanceMetrics()

    initial = equity_curve[0]
    final = equity_curve[-1]
    total_return = (final - initial) / initial if initial > 0 else 0.0

    n_periods = len(equity_curve) - 1
    annualized_return = (
        ((1 + total_return) ** (periods_per_year / n_periods)) - 1
        if n_periods > 0
        else 0.0
    )

    returns = []
    for i in range(1, len(equity_curve)):
        if equity_curve[i - 1] > 0:
            returns.append(
                (equity_curve[i] - equity_curve[i - 1]) / equity_curve[i - 1]
            )
        else:
            returns.append(0.0)

    mean_return = sum(returns) / len(returns) if returns else 0.0
    excess_returns = [r - risk_free_rate / periods_per_year for r in returns]

    variance = (
        sum((r - mean_return) ** 2 for r in returns) / (len(returns) - 1)
        if len(returns) > 1
        else 0.0
    )
    std_dev = sqrt(variance) if variance > 0 else 0.0
    sharpe_ratio = (
        (mean_return - risk_free_rate / periods_per_year) / std_dev * sqrt(periods_per_year)
        if std_dev > 0
        else 0.0
    )

    downside_returns = [r for r in excess_returns if r < 0]
    downside_variance = (
        sum(r**2 for r in downside_returns) / len(downside_returns)
        if downside_returns
        else 0.0
    )
    downside_dev = sqrt(downside_variance) if downside_variance > 0 else 0.0
    sortino_ratio = (
        (mean_return - risk_free_rate / periods_per_year) / downside_dev * sqrt(periods_per_year)
        if downside_dev > 0
        else 0.0
    )

    drawdowns, max_dd_duration = _compute_drawdowns(equity_curve)
    max_drawdown = drawdowns[0] if drawdowns else 0.0
    calmar_ratio = (
        annualized_return / max_drawdown if max_drawdown > 0 else 0.0
    )

    total_trades = len(trade_pnls)
    winning = [p for p in trade_pnls if p > 0]
    losing = [p for p in trade_pnls if p < 0]
    win_rate = len(winning) / total_trades if total_trades > 0 else 0.0
    gross_profit = sum(winning)
    gross_loss = abs(sum(losing))
    profit_factor = (
        gross_profit / gross_loss if gross_loss > 0 else 0.0
    )
    avg_win = sum(winning) / len(winning) if winning else 0.0
    avg_loss = sum(losing) / len(losing) if losing else 0.0
    avg_holding = (
        sum(trade_holding_periods) / len(trade_holding_periods)
        if trade_holding_periods
        else 0.0
    )

    net_pnl = sum(trade_pnls) - total_costs
    expectancy = net_pnl / total_trades if total_trades > 0 else 0.0

    kelly_fraction = 0.0
    if win_rate > 0 and avg_loss != 0:
        win_loss_ratio = abs(avg_win / avg_loss)
        kelly_fraction = win_rate - ((1 - win_rate) / win_loss_ratio)
        kelly_fraction = max(0.0, min(1.0, kelly_fraction))

    return PerformanceMetrics(
        total_return=total_return,
        annualized_return=annualized_return,
        sharpe_ratio=sharpe_ratio,
        sortino_ratio=sortino_ratio,
        max_drawdown=max_drawdown,
        max_drawdown_duration=max_dd_duration,
        calmar_ratio=calmar_ratio,
        profit_factor=profit_factor,
        win_rate=win_rate,
        total_trades=total_trades,
        winning_trades=len(winning),
        losing_trades=len(losing),
        avg_win=avg_win,
        avg_loss=avg_loss,
        avg_holding_periods=avg_holding,
        total_costs=total_costs,
        net_pnl=net_pnl,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        expectancy=expectancy,
        kelly_fraction=kelly_fraction,
    )
