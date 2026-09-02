from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class CostBreakdown:
    commission: float = 0.0
    slippage: float = 0.0
    spread: float = 0.0

    @property
    def total(self) -> float:
        return self.commission + self.slippage + self.spread


class CostModel(ABC):
    @abstractmethod
    def compute(
        self,
        price: float,
        quantity: float,
        side: str,
        bar_volume: float = 0.0,
    ) -> CostBreakdown: ...


class NoCostModel(CostModel):
    def compute(
        self,
        price: float,
        quantity: float,
        side: str,
        bar_volume: float = 0.0,
    ) -> CostBreakdown:
        return CostBreakdown()


@dataclass(frozen=True)
class FixedCostModel(CostModel):
    commission_rate: float = 0.001
    slippage_bps: float = 5.0
    spread_bps: float = 2.0

    def compute(
        self,
        price: float,
        quantity: float,
        side: str,
        bar_volume: float = 0.0,
    ) -> CostBreakdown:
        notional = abs(price * quantity)
        commission = notional * self.commission_rate
        slippage = notional * (self.slippage_bps / 10_000)
        spread = notional * (self.spread_bps / 10_000)
        return CostBreakdown(
            commission=commission,
            slippage=slippage,
            spread=spread,
        )


@dataclass(frozen=True)
class SlippageModel(CostModel):
    base_bps: float = 5.0
    volume_impact_factor: float = 0.1
    commission_rate: float = 0.001
    spread_bps: float = 2.0

    def compute(
        self,
        price: float,
        quantity: float,
        side: str,
        bar_volume: float = 0.0,
    ) -> CostBreakdown:
        notional = abs(price * quantity)
        commission = notional * self.commission_rate
        base_slippage = notional * (self.base_bps / 10_000)
        if bar_volume > 0:
            participation = abs(quantity) / bar_volume
            volume_impact = notional * self.volume_impact_factor * participation
        else:
            volume_impact = 0.0
        slippage = base_slippage + volume_impact
        spread = notional * (self.spread_bps / 10_000)
        return CostBreakdown(
            commission=commission,
            slippage=slippage,
            spread=spread,
        )
