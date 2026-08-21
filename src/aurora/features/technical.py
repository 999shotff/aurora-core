from aurora.features.base import FeatureExtractor, FeatureVector
from aurora.schemas.market_state import MarketStateSequence


class TechnicalFeatures(FeatureExtractor):
    extractor_id = "technical_v1"

    def extract(self, sequence: MarketStateSequence) -> FeatureVector:
        state = sequence.latest
        numerical: dict[str, float] = {}
        categorical: dict[str, str] = {}

        numerical["price"] = state.price

        if state.return_1h is not None:
            numerical["return_1h"] = state.return_1h
        if state.return_4h is not None:
            numerical["return_4h"] = state.return_4h

        categorical["structure_direction"] = state.structure.direction
        numerical["structure_bos"] = float(state.structure.bos)
        numerical["structure_choch"] = float(state.structure.choch)

        if state.structure.swing_high is not None and state.structure.swing_low is not None:
            range_val = state.structure.swing_high - state.structure.swing_low
            if range_val > 0:
                numerical["swing_range"] = range_val
                numerical["price_position_in_range"] = (
                    (state.price - state.structure.swing_low) / range_val
                )

        numerical["liquidity_strength"] = state.liquidity.strength
        numerical["liquidity_buy_sweep"] = float(state.liquidity.buy_side_sweep)
        numerical["liquidity_sell_sweep"] = float(state.liquidity.sell_side_sweep)

        if state.volume.relative_volume is not None:
            numerical["relative_volume"] = state.volume.relative_volume
        if state.volume.delta is not None:
            numerical["volume_delta"] = state.volume.delta

        if state.volatility.atr is not None:
            numerical["atr"] = state.volatility.atr
        if state.volatility.realized_volatility is not None:
            numerical["realized_volatility"] = state.volatility.realized_volatility
        categorical["volatility_regime"] = state.volatility.regime

        if state.vwap_distance_pct is not None:
            numerical["vwap_distance_pct"] = state.vwap_distance_pct

        if state.fibonacci_levels:
            numerical["fib_count"] = float(len(state.fibonacci_levels))
            fib_values = list(state.fibonacci_levels.values())
            if fib_values:
                numerical["fib_min"] = min(fib_values)
                numerical["fib_max"] = max(fib_values)

        numerical["historical_analogue_count"] = float(state.historical_analogue_count)

        categorical["data_quality"] = state.data_quality

        if sequence.window_size >= 2:
            seq_returns = sequence.returns()
            if seq_returns:
                numerical["seq_mean_return"] = sum(seq_returns) / len(seq_returns)
                numerical["seq_max_return"] = max(seq_returns)
                numerical["seq_min_return"] = min(seq_returns)
                numerical["seq_return_std"] = (
                    (sum((r - sum(seq_returns) / len(seq_returns)) ** 2 for r in seq_returns)
                    / len(seq_returns)) ** 0.5
                )
            prices = sequence.prices()
            numerical["seq_price_range"] = max(prices) - min(prices)

        return FeatureVector(
            extractor_id=self.extractor_id,
            asset=state.asset,
            timeframe=state.timeframe,
            timestamp=state.timestamp,
            numerical=numerical,
            categorical=categorical,
            metadata={"schema_version": state.schema_version, "window_size": sequence.window_size},
        )
