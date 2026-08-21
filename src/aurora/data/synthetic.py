from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone

from aurora.schemas.market_data import OHLCVBar, OHLCVSequence


def generate_synthetic_ohlcv(
    asset: str,
    timeframe: str = "1h",
    num_bars: int = 100,
    base_price: float = 100.0,
    base_volume: float = 1000.0,
    start_time: datetime | None = None,
    seed: int = 42,
) -> OHLCVSequence:
    if start_time is None:
        start_time = datetime(2025, 1, 1, 0, 0, tzinfo=timezone.utc)

    bars: list[OHLCVBar] = []
    current_price = base_price

    for i in range(num_bars):
        h = hashlib.sha256(f"{seed}:{i}".encode()).hexdigest()
        drift = (int(h[:8], 16) % 200 - 100) / 10000.0
        volatility = (int(h[8:16], 16) % 100) / 10000.0

        open_price = current_price
        change = current_price * drift
        close_price = current_price + change

        high_extra = current_price * volatility * 0.5
        low_extra = current_price * volatility * 0.5

        high_price = max(open_price, close_price) + high_extra
        low_price = min(open_price, close_price) - low_extra

        vol = base_volume * (0.5 + (int(h[16:24], 16) % 100) / 100.0)

        ts = start_time + timedelta(hours=i)

        bar = OHLCVBar(
            timestamp=ts,
            open=round(open_price, 2),
            high=round(high_price, 2),
            low=round(low_price, 2),
            close=round(close_price, 2),
            volume=round(vol, 2),
            asset=asset,
            timeframe=timeframe,
            source="synthetic",
            data_quality="simulated",
        )
        bars.append(bar)
        current_price = close_price

    return OHLCVSequence(asset=asset, timeframe=timeframe, bars=bars)
