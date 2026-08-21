"""Pre-registered feature set and interaction definitions."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class FeatureFamily(Enum):
    LIQUIDITY = "liquidity"
    MARKET_STRUCTURE = "market_structure"
    RSI = "rsi"
    MOMENTUM = "momentum"
    VOLATILITY = "volatility"
    VOLUME = "volume"
    VWAP = "vwap"
    FIBONACCI = "fibonacci"


class InteractionType(Enum):
    PRODUCT = "product"
    RATIO = "ratio"
    CONDITIONAL = "conditional"
    CROSSOVER = "crossover"


@dataclass(frozen=True)
class FeatureSpec:
    feature_id: str
    family: FeatureFamily
    description: str
    formula: str
    source_claim_id: str


@dataclass(frozen=True)
class InteractionSpec:
    interaction_id: str
    feature_a: str
    feature_b: str
    interaction_type: InteractionType
    formula: str
    description: str


@dataclass(frozen=True)
class PreRegisteredFeatureSet:
    version: str
    features: tuple[FeatureSpec, ...]
    interactions: tuple[InteractionSpec, ...]

    def feature_ids(self) -> list[str]:
        return [f.feature_id for f in self.features]

    def interaction_ids(self) -> list[str]:
        return [i.interaction_id for i in self.interactions]


def build_feature_registry() -> PreRegisteredFeatureSet:
    features = (
        FeatureSpec(
            feature_id="liquidity_sweep",
            family=FeatureFamily.LIQUIDITY,
            description="Liquidity sweep detection: price exceeds recent swing then reverses",
            formula="sweep = 1 if low < prev_low and close > prev_low; -1 if high > prev_high and close < prev_high",
            source_claim_id="b2280f4443f2611f_p9_c07acebd0",
        ),
        FeatureSpec(
            feature_id="market_structure_bos",
            family=FeatureFamily.MARKET_STRUCTURE,
            description="Break of Structure: price breaks above previous swing high or below swing low",
            formula="bos = 1 if close > prev_swing_high; -1 if close < prev_swing_low",
            source_claim_id="5fcfe5efce295a41_p24_c0f91a7e9",
        ),
        FeatureSpec(
            feature_id="rsi_signal",
            family=FeatureFamily.RSI,
            description="RSI oversold/overbought signal",
            formula="rsi_signal = 1 if RSI(14) < 30; -1 if RSI(14) > 70",
            source_claim_id="5fcfe5efce295a41_p3_c58d9f01b",
        ),
        FeatureSpec(
            feature_id="momentum_14",
            family=FeatureFamily.MOMENTUM,
            description="14-period price momentum",
            formula="mom = (close - close[14]) / close[14]",
            source_claim_id="5fcfe5efce295a41_p5_ce70606c3",
        ),
        FeatureSpec(
            feature_id="atr_ratio",
            family=FeatureFamily.VOLATILITY,
            description="ATR expansion ratio (short/long)",
            formula="atr_ratio = ATR(14) / ATR(50)",
            source_claim_id="0973976867d6b506_p97_c32ec2c40",
        ),
        FeatureSpec(
            feature_id="volume_divergence",
            family=FeatureFamily.VOLUME,
            description="Volume-price divergence: price trend vs volume trend",
            formula="div = -1 if price_slope > 0 and vol_slope < 0; 1 if price_slope < 0 and vol_slope > 0",
            source_claim_id="6cc3bf8840a7e6d9",
        ),
        FeatureSpec(
            feature_id="vwap_deviation",
            family=FeatureFamily.VWAP,
            description="Price deviation from VWAP",
            formula="vwap_dev = (close - VWAP) / VWAP",
            source_claim_id="2e15dafca208257c_p7_c33570093",
        ),
        FeatureSpec(
            feature_id="fibonacci_distance",
            family=FeatureFamily.FIBONACCI,
            description="Distance from 0.618 Fibonacci retracement level",
            formula="fib_dist = (close - (low + 0.618 * (high - low))) / close",
            source_claim_id="3d88aa766403f953_p295_cadcf2be2",
        ),
    )

    interactions = (
        InteractionSpec(
            interaction_id="liquidity_x_structure",
            feature_a="liquidity_sweep",
            feature_b="market_structure_bos",
            interaction_type=InteractionType.PRODUCT,
            formula="interaction = liquidity_sweep * market_structure_bos",
            description="Liquidity sweep combined with structure break direction",
        ),
        InteractionSpec(
            interaction_id="rsi_x_structure",
            feature_a="rsi_signal",
            feature_b="market_structure_bos",
            interaction_type=InteractionType.CONDITIONAL,
            formula="interaction = rsi_signal if market_structure_bos == 0 else market_structure_bos",
            description="RSI signal filtered by structure break",
        ),
        InteractionSpec(
            interaction_id="momentum_x_volatility",
            feature_a="momentum_14",
            feature_b="atr_ratio",
            interaction_type=InteractionType.PRODUCT,
            formula="interaction = momentum_14 * atr_ratio",
            description="Momentum scaled by volatility regime",
        ),
        InteractionSpec(
            interaction_id="volume_x_structure",
            feature_a="volume_divergence",
            feature_b="market_structure_bos",
            interaction_type=InteractionType.PRODUCT,
            formula="interaction = volume_divergence * market_structure_bos",
            description="Volume divergence confirmed by structure break",
        ),
        InteractionSpec(
            interaction_id="liquidity_x_volatility",
            feature_a="liquidity_sweep",
            feature_b="atr_ratio",
            interaction_type=InteractionType.PRODUCT,
            formula="interaction = liquidity_sweep * atr_ratio",
            description="Liquidity sweep in volatility context",
        ),
    )

    return PreRegisteredFeatureSet(
        version="1.0.0",
        features=tuple(features),
        interactions=tuple(interactions),
    )
