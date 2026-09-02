from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum


class PositionSide(str, Enum):
    LONG = "long"
    SHORT = "short"
    FLAT = "flat"


@dataclass(frozen=True)
class Fill:
    timestamp: datetime
    price: float
    quantity: float
    side: PositionSide
    cost: float = 0.0
    slippage: float = 0.0

    @property
    def notional(self) -> float:
        return abs(self.price * self.quantity)


@dataclass
class Trade:
    entry: Fill
    exit: Fill | None = None
    pnl: float = 0.0
    pnl_pct: float = 0.0
    holding_periods: int = 0

    @property
    def is_open(self) -> bool:
        return self.exit is None

    def close(self, exit_fill: Fill) -> None:
        self.exit = exit_fill
        if self.entry.side == PositionSide.LONG:
            self.pnl = (exit_fill.price - self.entry.price) * self.entry.quantity
            self.pnl_pct = (
                (exit_fill.price - self.entry.price) / self.entry.price
                if self.entry.price != 0
                else 0.0
            )
        else:
            self.pnl = (self.entry.price - exit_fill.price) * self.entry.quantity
            self.pnl_pct = (
                (self.entry.price - exit_fill.price) / self.entry.price
                if self.entry.price != 0
                else 0.0
            )
        self.pnl -= (self.entry.cost + (exit_fill.cost if exit_fill else 0.0))


@dataclass
class PositionTracker:
    entry_price: float = 0.0
    quantity: float = 0.0
    side: PositionSide = PositionSide.FLAT
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    total_cost: float = 0.0
    trades: list[Trade] = field(default_factory=list)
    current_trade: Trade | None = None
    holding_periods: int = 0

    @property
    def is_flat(self) -> bool:
        return self.side == PositionSide.FLAT or self.quantity == 0.0

    @property
    def notional(self) -> float:
        return abs(self.entry_price * self.quantity)

    def open_position(
        self, fill: Fill, holding_period_start: int = 0
    ) -> None:
        if not self.is_flat:
            return
        self.entry_price = fill.price
        self.quantity = fill.quantity
        self.side = (
            PositionSide.LONG
            if fill.side == PositionSide.LONG
            else PositionSide.SHORT
        )
        self.total_cost += fill.cost
        self.current_trade = Trade(entry=fill)
        self.holding_periods = 0

    def close_position(self, fill: Fill) -> Trade | None:
        if self.is_flat or self.current_trade is None:
            return None
        self.current_trade.holding_periods = self.holding_periods
        self.current_trade.close(fill)
        self.total_cost += fill.cost
        self.realized_pnl += self.current_trade.pnl
        trade = self.current_trade
        self.trades.append(trade)
        self.current_trade = None
        self.entry_price = 0.0
        self.quantity = 0.0
        self.side = PositionSide.FLAT
        self.unrealized_pnl = 0.0
        self.holding_periods = 0
        return trade

    def update_unrealized(self, current_price: float) -> None:
        if self.is_flat:
            self.unrealized_pnl = 0.0
            return
        if self.side == PositionSide.LONG:
            self.unrealized_pnl = (
                current_price - self.entry_price
            ) * self.quantity
        else:
            self.unrealized_pnl = (
                self.entry_price - current_price
            ) * self.quantity

    def increment_holding(self) -> None:
        self.holding_periods += 1
