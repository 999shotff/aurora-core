from __future__ import annotations

from aurora.features.base import FeatureExtractor, FeatureVector
from aurora.schemas.market_data import OHLCVBar, OHLCVSequence
from aurora.schemas.market_state import (
    MarketState,
    MarketStateSequence,
    VolatilityState,
    VolumeState,
)


def ohlcv_to_market_state(
    bar: OHLCVBar,
    data_quality: str = "historical",
) -> MarketState:
    return MarketState(
        asset=bar.asset,
        timeframe=bar.timeframe,
        timestamp=bar.timestamp,
        data_quality=data_quality,  # type: ignore[arg-type]
        price=bar.close,
        volume=VolumeState(
            relative_volume=None,
            delta=None,
            delta_available=False,
        ),
        volatility=VolatilityState(
            atr=None,
            realized_volatility=None,
            regime="unknown",
        ),
    )


def ohlcv_sequence_to_market_state_sequence(
    sequence: OHLCVSequence,
) -> MarketStateSequence:
    snapshots = []
    for bar in sequence.bars:
        state = ohlcv_to_market_state(bar, data_quality=sequence.bars[0].data_quality)
        snapshots.append(state)
    return MarketStateSequence(
        asset=sequence.asset,
        timeframe=sequence.timeframe,
        snapshots=snapshots,
    )


class MarketDataPipeline:
    def __init__(self, extractors: list[FeatureExtractor] | None = None):
        self._extractors = extractors or []

    def run(
        self, sequence: OHLCVSequence
    ) -> tuple[MarketStateSequence, list[FeatureVector]]:
        mss = ohlcv_sequence_to_market_state_sequence(sequence)
        vectors: list[FeatureVector] = []
        for ext in self._extractors:
            vec = ext.extract(mss)
            vectors.append(vec)
        return mss, vectors

    def run_single(
        self, sequence: OHLCVSequence, extractor: FeatureExtractor
    ) -> FeatureVector:
        mss = ohlcv_sequence_to_market_state_sequence(sequence)
        return extractor.extract(mss)
