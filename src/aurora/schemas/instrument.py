from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

AssetClass = Literal["crypto", "equity", "forex", "commodity", "derivative", "other"]
ExchangeType = Literal["spot", "perpetual", "futures", "options", "other"]


class InstrumentIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid", protected_namespaces=())

    symbol: str
    asset_class: AssetClass
    exchange: str = "unknown"
    quote_currency: str = "USD"
    source_timezone: str = "UTC"
    instrument_type: ExchangeType = "spot"
    display_name: str = ""
    decimals: int = 8
    min_tick_size: float = Field(default=0.01, gt=0.0)
    contract_size: float = Field(default=1.0, gt=0.0)
    metadata: dict[str, str | int | float | bool] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _set_display_name(self) -> InstrumentIdentity:
        if not self.display_name:
            self.display_name = self.symbol.upper()
        return self

    @property
    def base_currency(self) -> str:
        parts = self.symbol.upper().replace("/", "").split(self.quote_currency.upper())
        if len(parts) == 2 and parts[0]:
            return parts[0]
        return self.symbol.upper()

    def canonical_name(self) -> str:
        return f"{self.symbol.upper()}:{self.asset_class}:{self.exchange}"

    def matches(self, other: InstrumentIdentity) -> bool:
        return self.symbol.upper() == other.symbol.upper()


def build_instrument(
    symbol: str,
    asset_class: AssetClass = "crypto",
    exchange: str = "unknown",
    quote_currency: str = "USD",
    metadata: dict[str, str | int | float | bool] | None = None,
    decimals: int = 8,
    min_tick_size: float = 0.01,
    contract_size: float = 1.0,
) -> InstrumentIdentity:
    return InstrumentIdentity(
        symbol=symbol.upper(),
        asset_class=asset_class,
        exchange=exchange,
        quote_currency=quote_currency.upper(),
        metadata=metadata or {},
        decimals=decimals,
        min_tick_size=min_tick_size,
        contract_size=contract_size,
    )
