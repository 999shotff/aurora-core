from __future__ import annotations

import math
from datetime import datetime, timedelta, timezone

from aurora.schemas.market_data import OHLCVBar, OHLCVSequence


def generate_realistic_ohlcv(
    asset: str = "BTCUSD",
    timeframe: str = "1h",
    num_bars: int = 8760,
    base_price: float = 30000.0,
    annual_drift: float = 0.0,
    annual_vol: float = 0.8,
    mean_revert_speed: float = 0.01,
    mean_revert_target: float = 0.0,
    seed: int = 42,
) -> OHLCVSequence:
    start_time = datetime(2022, 1, 1, 0, 0, tzinfo=timezone.utc)
    hours_per_year = 8760
    dt = 1.0 / hours_per_year
    drift_per_bar = annual_drift * dt
    vol_per_bar = annual_vol * math.sqrt(dt)

    bars: list[OHLCVBar] = []
    price = base_price
    log_price = math.log(price)
    log_mean = math.log(base_price) + mean_revert_target

    rng_state = seed

    def _next_random() -> float:
        nonlocal rng_state
        rng_state = (rng_state * 1103515245 + 12345) & 0x7FFFFFFF
        return rng_state / 0x7FFFFFFF

    def _box_muller() -> float:
        u1 = max(_next_random(), 1e-10)
        u2 = _next_random()
        return math.sqrt(-2 * math.log(u1)) * math.cos(2 * math.pi * u2)

    for i in range(num_bars):
        z = _box_muller()
        drift = (drift_per_bar - mean_revert_speed * (log_price - log_mean)) * 1.0
        diffusion = vol_per_bar * z
        log_price += drift + diffusion
        price = math.exp(log_price)

        intra_vol = vol_per_bar * 0.3
        high_extra = price * abs(_box_muller()) * intra_vol
        low_extra = price * abs(_box_muller()) * intra_vol

        open_price = price * (1 + _box_muller() * vol_per_bar * 0.1)
        close_price = price
        high_price = max(open_price, close_price) + high_extra
        low_price = min(open_price, close_price) - low_extra

        base_vol = 1000.0 * (1 + 0.5 * abs(_box_muller()))
        volume = max(base_vol, 1.0)

        ts = start_time + timedelta(hours=i)

        bar = OHLCVBar(
            timestamp=ts,
            open=round(open_price, 2),
            high=round(high_price, 2),
            low=round(max(low_price, 0.01), 2),
            close=round(close_price, 2),
            volume=round(volume, 2),
            asset=asset,
            timeframe=timeframe,
            source="synthetic_realistic",
            data_quality="simulated",
        )
        bars.append(bar)

    return OHLCVSequence(asset=asset, timeframe=timeframe, bars=bars)
