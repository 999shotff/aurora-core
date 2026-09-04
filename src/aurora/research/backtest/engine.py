from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from aurora.research.backtest.costs import CostModel, NoCostModel
from aurora.research.backtest.data_model import Dataset
from aurora.research.backtest.metrics import PerformanceMetrics, compute_metrics
from aurora.research.backtest.position import Fill, PositionSide, PositionTracker
from aurora.research.backtest.risk import RiskMetrics, compute_risk_metrics
from aurora.research.backtest.strategy import Side, Signal, Strategy


@dataclass
class BacktestResult:
    equity_curve: list[float] = field(default_factory=list)
    timestamps: list[datetime] = field(default_factory=list)
    signals: list[Signal] = field(default_factory=list)
    fills: list[Fill] = field(default_factory=list)
    metrics: PerformanceMetrics = field(default_factory=PerformanceMetrics)
    risk: RiskMetrics = field(default_factory=RiskMetrics)
    positions: list[dict[str, Any]] = field(default_factory=list)
    total_cost: float = 0.0
    initial_equity: float = 0.0
    final_equity: float = 0.0

    @property
    def net_return(self) -> float:
        if self.initial_equity == 0:
            return 0.0
        return (self.final_equity - self.initial_equity) / self.initial_equity

    def summary(self) -> dict[str, Any]:
        return {
            "initial_equity": self.initial_equity,
            "final_equity": self.final_equity,
            "net_return": self.net_return,
            "total_trades": self.metrics.total_trades,
            "win_rate": self.metrics.win_rate,
            "sharpe_ratio": self.metrics.sharpe_ratio,
            "max_drawdown": self.metrics.max_drawdown,
            "total_cost": self.total_cost,
            "net_pnl": self.metrics.net_pnl,
        }


class BacktestEngine:
    def __init__(
        self,
        strategy: Strategy,
        cost_model: CostModel | None = None,
        initial_equity: float = 100_000.0,
        position_size: float = 1.0,
        max_positions: int = 1,
    ) -> None:
        self.strategy = strategy
        self.cost_model = cost_model or NoCostModel()
        self.initial_equity = initial_equity
        self.position_size = position_size
        self.max_positions = max_positions

    def run(self, dataset: Dataset) -> BacktestResult:
        errors = dataset.validate_chronological()
        if errors:
            raise ValueError(
                f"Dataset has {len(errors)} chronological errors: {errors[:3]}"
            )

        self.strategy.on_start(dataset)

        tracker = PositionTracker()
        equity = self.initial_equity
        equity_curve = [equity]
        timestamps = [dataset.bars[0].timestamp]
        all_signals: list[Signal] = []
        all_fills: list[Fill] = []
        all_positions: list[dict[str, Any]] = []

        lookback = getattr(self.strategy, "_config", None)
        lb = lookback.lookback if lookback else 0

        for i, bar in enumerate(dataset.bars):
            start_idx = max(0, i - lb) if lb > 0 else 0
            history = dataset.bars[start_idx:i]

            signal = self.strategy.on_bar(
                bar=bar,
                history=history,
                position=tracker.quantity,
                equity=equity,
            )
            all_signals.append(signal)

            if signal.side == Side.LONG and tracker.is_flat:
                qty = self._compute_quantity(
                    equity, bar.close, signal.strength
                )
                if qty > 0:
                    cost_bd = self.cost_model.compute(
                        bar.close, qty, "buy", bar.volume
                    )
                    fill = Fill(
                        timestamp=bar.timestamp,
                        price=bar.close,
                        quantity=qty,
                        side=PositionSide.LONG,
                        cost=cost_bd.total,
                    )
                    tracker.open_position(fill)
                    equity -= cost_bd.total
                    all_fills.append(fill)

            elif signal.side == Side.SHORT and tracker.is_flat:
                qty = self._compute_quantity(
                    equity, bar.close, signal.strength
                )
                if qty > 0:
                    cost_bd = self.cost_model.compute(
                        bar.close, qty, "sell", bar.volume
                    )
                    fill = Fill(
                        timestamp=bar.timestamp,
                        price=bar.close,
                        quantity=qty,
                        side=PositionSide.SHORT,
                        cost=cost_bd.total,
                    )
                    tracker.open_position(fill)
                    equity -= cost_bd.total
                    all_fills.append(fill)

            elif signal.side == Side.FLAT and not tracker.is_flat:
                exit_price = bar.close
                if tracker.side == PositionSide.LONG and signal.stop_loss:
                    if bar.low <= signal.stop_loss:
                        exit_price = signal.stop_loss
                elif tracker.side == PositionSide.SHORT and signal.stop_loss:
                    if bar.high >= signal.stop_loss:
                        exit_price = signal.stop_loss

                cost_bd = self.cost_model.compute(
                    exit_price, tracker.quantity, "sell", bar.volume
                )
                exit_side = (
                    PositionSide.SHORT
                    if tracker.side == PositionSide.LONG
                    else PositionSide.LONG
                )
                fill = Fill(
                    timestamp=bar.timestamp,
                    price=exit_price,
                    quantity=tracker.quantity,
                    side=exit_side,
                    cost=cost_bd.total,
                )
                trade = tracker.close_position(fill)
                equity -= cost_bd.total
                equity += tracker.realized_pnl
                all_fills.append(fill)
                if trade:
                    all_positions.append({
                        "entry_time": trade.entry.timestamp.isoformat(),
                        "exit_time": (
                            trade.exit.timestamp.isoformat()
                            if trade.exit
                            else None
                        ),
                        "side": tracker.side.value,
                        "pnl": trade.pnl,
                        "pnl_pct": trade.pnl_pct,
                        "holding_periods": trade.holding_periods,
                    })

            tracker.update_unrealized(bar.close)
            tracker.increment_holding()
            equity_with_unrealized = equity + tracker.unrealized_pnl
            equity_curve.append(equity_with_unrealized)
            timestamps.append(bar.timestamp)

        if not tracker.is_flat:
            last_bar = dataset.bars[-1]
            cost_bd = self.cost_model.compute(
                last_bar.close, tracker.quantity, "sell", last_bar.volume
            )
            exit_side = (
                PositionSide.SHORT
                if tracker.side == PositionSide.LONG
                else PositionSide.LONG
            )
            fill = Fill(
                timestamp=last_bar.timestamp,
                price=last_bar.close,
                quantity=tracker.quantity,
                side=exit_side,
                cost=cost_bd.total,
            )
            tracker.close_position(fill)
            equity -= cost_bd.total
            equity += tracker.realized_pnl
            all_fills.append(fill)

        self.strategy.on_end()

        trade_pnls = [t.pnl for t in tracker.trades]
        trade_holdings = [t.holding_periods for t in tracker.trades]
        total_cost = tracker.total_cost

        metrics = compute_metrics(
            equity_curve=equity_curve,
            trade_pnls=trade_pnls,
            trade_holding_periods=trade_holdings,
            total_costs=total_cost,
        )
        risk = compute_risk_metrics(equity_curve)

        return BacktestResult(
            equity_curve=equity_curve,
            timestamps=timestamps,
            signals=all_signals,
            fills=all_fills,
            metrics=metrics,
            risk=risk,
            positions=all_positions,
            total_cost=total_cost,
            initial_equity=self.initial_equity,
            final_equity=equity_curve[-1] if equity_curve else self.initial_equity,
        )

    def _compute_quantity(
        self, equity: float, price: float, strength: float
    ) -> float:
        if price <= 0 or equity <= 0:
            return 0.0
        capital = equity * self.position_size * strength
        qty = capital / price
        return max(0.0, qty)
