"""Context-aware methodology taxonomy with weighted evidence.

Phase 4.5: Improves classification from ~82% UNKNOWN to significantly lower.
Uses weighted keyword evidence, multi-signal scoring, and confidence thresholds.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

MethodologyCategory = Literal[
    "liquidity",
    "market_structure",
    "order_flow",
    "volume",
    "vwap",
    "market_profile",
    "fibonacci",
    "gann",
    "elliott_wave",
    "volatility",
    "technical_analysis",
    "news",
    "market_psychology",
    "astrology",
    "time_cycles",
    "quantitative_finance",
    "machine_learning",
    "risk_management",
    "unknown",
]

METHODOLOGY_TAXONOMY: dict[MethodologyCategory, dict[str, str]] = {
    "liquidity": {
        "description": "Liquidity concepts, sweeps, levels, order blocks",
        "parent": "market_structure",
    },
    "market_structure": {
        "description": "BOS, CHoCH, swing structure, trend analysis",
        "parent": "technical_analysis",
    },
    "order_flow": {
        "description": "Delta, cumulative delta, order book dynamics",
        "parent": "volume",
    },
    "volume": {
        "description": "Volume analysis, profile, OBV, divergence",
        "parent": "technical_analysis",
    },
    "vwap": {
        "description": "VWAP, deviation bands, anchor points",
        "parent": "volume",
    },
    "market_profile": {
        "description": "TPO, value area, profile distributions",
        "parent": "volume",
    },
    "fibonacci": {
        "description": "Fibonacci retracements, extensions, time zones",
        "parent": "technical_analysis",
    },
    "gann": {
        "description": "Gann angles, squares, time cycles, vibration theory",
        "parent": "technical_analysis",
    },
    "elliott_wave": {
        "description": "Elliott wave patterns, impulse, correction",
        "parent": "technical_analysis",
    },
    "volatility": {
        "description": "ATR, realized vol, implied vol, regimes",
        "parent": "technical_analysis",
    },
    "technical_analysis": {
        "description": "General chart patterns, indicators, price action",
        "parent": "",
    },
    "news": {
        "description": "News impact, event-driven analysis",
        "parent": "",
    },
    "market_psychology": {
        "description": "Sentiment, positioning, crowd behavior",
        "parent": "",
    },
    "astrology": {
        "description": "Astrological market analysis (experimental)",
        "parent": "",
    },
    "time_cycles": {
        "description": "Seasonal, cyclical, calendar effects",
        "parent": "",
    },
    "quantitative_finance": {
        "description": "Statistical models, factor models, risk parity",
        "parent": "",
    },
    "machine_learning": {
        "description": "ML-based prediction, pattern recognition",
        "parent": "",
    },
    "risk_management": {
        "description": "Position sizing, stop loss, portfolio construction",
        "parent": "",
    },
    "unknown": {
        "description": "Unclassified methodology",
        "parent": "",
    },
}


@dataclass
class KeywordWeight:
    keyword: str
    weight: float
    case_sensitive: bool = False


@dataclass
class MethodologyProfile:
    category: MethodologyCategory
    primary_keywords: list[KeywordWeight] = field(default_factory=list)
    secondary_keywords: list[KeywordWeight] = field(default_factory=list)
    context_keywords: list[KeywordWeight] = field(default_factory=list)
    min_score: float = 0.3


PROFILES: dict[str, MethodologyProfile] = {
    "fibonacci": MethodologyProfile(
        category="fibonacci",
        primary_keywords=[
            KeywordWeight("fibonacci", 1.0),
            KeywordWeight("fib ", 0.8),
            KeywordWeight("fibonacci retracement", 1.0),
            KeywordWeight("fibonacci extension", 1.0),
            KeywordWeight("fibonacci level", 1.0),
        ],
        secondary_keywords=[
            KeywordWeight("0.618", 0.9),
            KeywordWeight("0.382", 0.9),
            KeywordWeight("0.236", 0.8),
            KeywordWeight("1.618", 0.8),
            KeywordWeight("2.618", 0.7),
            KeywordWeight("retracement", 0.5),
            KeywordWeight("extension", 0.3),
            KeywordWeight("golden ratio", 0.7),
        ],
        context_keywords=[
            KeywordWeight("support", 0.2),
            KeywordWeight("resistance", 0.2),
            KeywordWeight("level", 0.1),
            KeywordWeight("price", 0.1),
        ],
        min_score=0.4,
    ),
    "gann": MethodologyProfile(
        category="gann",
        primary_keywords=[
            KeywordWeight("gann", 1.0),
            KeywordWeight("gann angle", 1.0),
            KeywordWeight("gann square", 1.0),
            KeywordWeight("gann fan", 1.0),
            KeywordWeight("gann line", 1.0),
        ],
        secondary_keywords=[
            KeywordWeight("vibration", 0.7),
            KeywordWeight("law of vibration", 0.9),
            KeywordWeight("geometric", 0.4),
            KeywordWeight("angle", 0.3),
            KeywordWeight("squaring", 0.6),
            KeywordWeight("45 degree", 0.5),
            KeywordWeight("1x1 angle", 0.7),
            KeywordWeight("2x1 angle", 0.7),
        ],
        context_keywords=[
            KeywordWeight("time cycle", 0.3),
            KeywordWeight("price time", 0.3),
            KeywordWeight("natural square", 0.5),
        ],
        min_score=0.4,
    ),
    "elliott_wave": MethodologyProfile(
        category="elliott_wave",
        primary_keywords=[
            KeywordWeight("elliott wave", 1.0),
            KeywordWeight("elliott", 0.8),
            KeywordWeight("impulse wave", 0.9),
            KeywordWeight("corrective wave", 0.9),
            KeywordWeight("wave pattern", 0.8),
        ],
        secondary_keywords=[
            KeywordWeight("wave 1", 0.7),
            KeywordWeight("wave 2", 0.7),
            KeywordWeight("wave 3", 0.7),
            KeywordWeight("wave 4", 0.7),
            KeywordWeight("wave 5", 0.7),
            KeywordWeight("a-b-c", 0.8),
            KeywordWeight("impulse", 0.4),
            KeywordWeight("correction", 0.3),
            KeywordWeight("fibonacci", 0.3),
        ],
        context_keywords=[
            KeywordWeight("trend", 0.2),
            KeywordWeight("pattern", 0.1),
        ],
        min_score=0.4,
    ),
    "volatility": MethodologyProfile(
        category="volatility",
        primary_keywords=[
            KeywordWeight("volatility", 1.0),
            KeywordWeight("implied volatility", 1.0),
            KeywordWeight("realized volatility", 1.0),
            KeywordWeight("vol surface", 0.9),
        ],
        secondary_keywords=[
            KeywordWeight("atr", 0.7),
            KeywordWeight("average true range", 0.8),
            KeywordWeight("vix", 0.7),
            KeywordWeight("volatility regime", 0.8),
            KeywordWeight("volatility band", 0.7),
            KeywordWeight("bollinger", 0.5),
            KeywordWeight("standard deviation", 0.4),
            KeywordWeight("variance", 0.3),
            KeywordWeight("skew", 0.4),
            KeywordWeight("kurtosis", 0.4),
            KeywordWeight("options", 0.3),
            KeywordWeight("straddle", 0.5),
            KeywordWeight("strangle", 0.5),
        ],
        context_keywords=[
            KeywordWeight("risk", 0.2),
            KeywordWeight("measure", 0.1),
        ],
        min_score=0.35,
    ),
    "volume": MethodologyProfile(
        category="volume",
        primary_keywords=[
            KeywordWeight("volume analysis", 1.0),
            KeywordWeight("volume profile", 1.0),
            KeywordWeight("order volume", 0.8),
        ],
        secondary_keywords=[
            KeywordWeight("obv", 0.7),
            KeywordWeight("on balance volume", 0.8),
            KeywordWeight("volume weighted", 0.6),
            KeywordWeight("volume divergence", 0.8),
            KeywordWeight("volume climax", 0.7),
            KeywordWeight("accumulation", 0.5),
            KeywordWeight("distribution", 0.5),
            KeywordWeight("volume ratio", 0.6),
        ],
        context_keywords=[
            KeywordWeight("buying", 0.2),
            KeywordWeight("selling", 0.2),
            KeywordWeight("pressure", 0.1),
        ],
        min_score=0.35,
    ),
    "vwap": MethodologyProfile(
        category="vwap",
        primary_keywords=[
            KeywordWeight("vwap", 1.0),
            KeywordWeight("volume weighted average price", 1.0),
        ],
        secondary_keywords=[
            KeywordWeight("anchor vwap", 0.8),
            KeywordWeight("vwap band", 0.8),
            KeywordWeight("vwap deviation", 0.8),
            KeywordWeight("vwap upper", 0.7),
            KeywordWeight("vwap lower", 0.7),
            KeywordWeight("intraday vwap", 0.7),
        ],
        context_keywords=[
            KeywordWeight("average", 0.1),
            KeywordWeight("price", 0.1),
        ],
        min_score=0.4,
    ),
    "market_profile": MethodologyProfile(
        category="market_profile",
        primary_keywords=[
            KeywordWeight("market profile", 1.0),
            KeywordWeight("tpo", 0.9),
            KeywordWeight("time price opportunity", 1.0),
        ],
        secondary_keywords=[
            KeywordWeight("value area", 0.8),
            KeywordWeight("point of control", 0.8),
            KeywordWeight("poc", 0.7),
            KeywordWeight("value area high", 0.8),
            KeywordWeight("value area low", 0.8),
            KeywordWeight("d distribution", 0.6),
            KeywordWeight("b distribution", 0.6),
        ],
        context_keywords=[
            KeywordWeight("profile", 0.2),
            KeywordWeight("auction", 0.3),
        ],
        min_score=0.4,
    ),
    "liquidity": MethodologyProfile(
        category="liquidity",
        primary_keywords=[
            KeywordWeight("liquidity sweep", 1.0),
            KeywordWeight("liquidity grab", 1.0),
            KeywordWeight("liquidity level", 0.9),
            KeywordWeight("liquidity pool", 0.9),
            KeywordWeight("stop hunt", 0.8),
        ],
        secondary_keywords=[
            KeywordWeight("order block", 0.7),
            KeywordWeight("break of structure", 0.6),
            KeywordWeight("bos", 0.5),
            KeywordWeight("choch", 0.7),
            KeywordWeight("swing high", 0.4),
            KeywordWeight("swing low", 0.4),
            KeywordWeight("equal highs", 0.6),
            KeywordWeight("equal lows", 0.6),
            KeywordWeight("sell side", 0.5),
            KeywordWeight("buy side", 0.5),
            KeywordWeight("liquidity", 0.6),
        ],
        context_keywords=[
            KeywordWeight("price", 0.1),
            KeywordWeight("level", 0.1),
        ],
        min_score=0.35,
    ),
    "market_structure": MethodologyProfile(
        category="market_structure",
        primary_keywords=[
            KeywordWeight("market structure", 1.0),
            KeywordWeight("break of structure", 0.9),
            KeywordWeight("change of character", 0.9),
            KeywordWeight("choch", 0.8),
        ],
        secondary_keywords=[
            KeywordWeight("swing structure", 0.7),
            KeywordWeight("trend structure", 0.7),
            KeywordWeight("higher high", 0.6),
            KeywordWeight("higher low", 0.6),
            KeywordWeight("lower high", 0.6),
            KeywordWeight("lower low", 0.6),
            KeywordWeight("structure break", 0.7),
            KeywordWeight("market trend", 0.4),
        ],
        context_keywords=[
            KeywordWeight("trend", 0.2),
            KeywordWeight("price action", 0.2),
        ],
        min_score=0.35,
    ),
    "order_flow": MethodologyProfile(
        category="order_flow",
        primary_keywords=[
            KeywordWeight("order flow", 1.0),
            KeywordWeight("cumulative delta", 1.0),
            KeywordWeight("delta divergence", 0.9),
        ],
        secondary_keywords=[
            KeywordWeight("bid ask", 0.7),
            KeywordWeight("order book", 0.7),
            KeywordWeight("trade tape", 0.6),
            KeywordWeight("footprint", 0.6),
            KeywordWeight("volume footprint", 0.7),
            KeywordWeight("delta", 0.5),
            KeywordWeight("aggressive", 0.4),
            KeywordWeight("passive", 0.4),
            KeywordWeight("absorption", 0.5),
        ],
        context_keywords=[
            KeywordWeight("execution", 0.2),
            KeywordWeight("flow", 0.1),
        ],
        min_score=0.35,
    ),
    "technical_analysis": MethodologyProfile(
        category="technical_analysis",
        primary_keywords=[
            KeywordWeight("technical analysis", 1.0),
            KeywordWeight("chart pattern", 0.9),
            KeywordWeight("price action", 0.7),
        ],
        secondary_keywords=[
            KeywordWeight("moving average", 0.6),
            KeywordWeight("indicator", 0.5),
            KeywordWeight("support", 0.4),
            KeywordWeight("resistance", 0.4),
            KeywordWeight("trend line", 0.6),
            KeywordWeight("candlestick", 0.5),
            KeywordWeight("pattern", 0.3),
            KeywordWeight("breakout", 0.4),
            KeywordWeight("pullback", 0.3),
            KeywordWeight("reversal", 0.3),
            KeywordWeight("divergence", 0.4),
            KeywordWeight("rsi", 0.5),
            KeywordWeight("macd", 0.5),
            KeywordWeight("sma", 0.5),
            KeywordWeight("ema", 0.5),
            KeywordWeight("stochastic", 0.5),
        ],
        context_keywords=[
            KeywordWeight("chart", 0.2),
            KeywordWeight("price", 0.1),
            KeywordWeight("market", 0.1),
        ],
        min_score=0.3,
    ),
    "news": MethodologyProfile(
        category="news",
        primary_keywords=[
            KeywordWeight("news trading", 1.0),
            KeywordWeight("event driven", 0.9),
            KeywordWeight("news impact", 1.0),
        ],
        secondary_keywords=[
            KeywordWeight("earnings", 0.7),
            KeywordWeight("economic release", 0.8),
            KeywordWeight("non-farm", 0.7),
            KeywordWeight("fomc", 0.7),
            KeywordWeight("interest rate", 0.5),
            KeywordWeight("gdp", 0.5),
            KeywordWeight("inflation", 0.4),
            KeywordWeight("cpi", 0.5),
            KeywordWeight("payroll", 0.5),
            KeywordWeight("announcement", 0.4),
            KeywordWeight("headline", 0.5),
            KeywordWeight("fundamental", 0.3),
        ],
        context_keywords=[
            KeywordWeight("market", 0.1),
            KeywordWeight("price", 0.1),
        ],
        min_score=0.35,
    ),
    "market_psychology": MethodologyProfile(
        category="market_psychology",
        primary_keywords=[
            KeywordWeight("market psychology", 1.0),
            KeywordWeight("trading psychology", 1.0),
            KeywordWeight("crowd psychology", 1.0),
        ],
        secondary_keywords=[
            KeywordWeight("fear", 0.5),
            KeywordWeight("greed", 0.5),
            KeywordWeight("sentiment", 0.5),
            KeywordWeight("cognitive bias", 0.7),
            KeywordWeight("discipline", 0.4),
            KeywordWeight("emotion", 0.5),
            KeywordWeight("mindset", 0.5),
            KeywordWeight("behavioral", 0.5),
            KeywordWeight("positioning", 0.4),
            KeywordWeight("contrarian", 0.5),
            KeywordWeight("herd", 0.5),
            KeywordWeight("overconfidence", 0.6),
            KeywordWeight("loss aversion", 0.7),
            KeywordWeight("disposition effect", 0.7),
        ],
        context_keywords=[
            KeywordWeight("trader", 0.2),
            KeywordWeight("investor", 0.2),
        ],
        min_score=0.3,
    ),
    "astrology": MethodologyProfile(
        category="astrology",
        primary_keywords=[
            KeywordWeight("astrology", 1.0),
            KeywordWeight("astrological", 1.0),
            KeywordWeight("planetary", 0.8),
            KeywordWeight("planetary alignment", 1.0),
        ],
        secondary_keywords=[
            KeywordWeight("zodiac", 0.8),
            KeywordWeight("mercury retrograde", 0.9),
            KeywordWeight("lunar", 0.6),
            KeywordWeight("solar", 0.5),
            KeywordWeight("eclipse", 0.7),
            KeywordWeight("jupiter", 0.6),
            KeywordWeight("saturn", 0.6),
            KeywordWeight("mars", 0.5),
            KeywordWeight("venus", 0.5),
            KeywordWeight("transit", 0.5),
            KeywordWeight("ephemeris", 0.7),
            KeywordWeight("aspect", 0.3),
            KeywordWeight("conjunction", 0.5),
            KeywordWeight("opposition aspect", 0.5),
        ],
        context_keywords=[
            KeywordWeight("cycle", 0.2),
            KeywordWeight("time", 0.1),
        ],
        min_score=0.3,
    ),
    "time_cycles": MethodologyProfile(
        category="time_cycles",
        primary_keywords=[
            KeywordWeight("time cycle", 1.0),
            KeywordWeight("time cycles", 1.0),
            KeywordWeight("cyclical analysis", 1.0),
        ],
        secondary_keywords=[
            KeywordWeight("seasonal", 0.7),
            KeywordWeight("calendar effect", 0.8),
            KeywordWeight("cycle low", 0.7),
            KeywordWeight("cycle high", 0.7),
            KeywordWeight("periodicity", 0.7),
            KeywordWeight("hurst", 0.6),
            KeywordWeight("dominant cycle", 0.8),
            KeywordWeight("cycle length", 0.7),
            KeywordWeight("turning point", 0.5),
            KeywordWeight("cycle analysis", 0.8),
        ],
        context_keywords=[
            KeywordWeight("time", 0.2),
            KeywordWeight("date", 0.1),
        ],
        min_score=0.35,
    ),
    "quantitative_finance": MethodologyProfile(
        category="quantitative_finance",
        primary_keywords=[
            KeywordWeight("quantitative", 1.0),
            KeywordWeight("quant finance", 1.0),
            KeywordWeight("factor model", 1.0),
        ],
        secondary_keywords=[
            KeywordWeight("regression", 0.6),
            KeywordWeight("statistical", 0.5),
            KeywordWeight("correlation", 0.4),
            KeywordWeight("portfolio optimization", 0.7),
            KeywordWeight("sharpe ratio", 0.7),
            KeywordWeight("risk parity", 0.7),
            KeywordWeight("mean variance", 0.7),
            KeywordWeight("monte carlo", 0.6),
            KeywordWeight("stochastic process", 0.6),
            KeywordWeight("brownian motion", 0.6),
            KeywordWeight("black scholes", 0.7),
            KeywordWeight("implied vol", 0.4),
            KeywordWeight("delta hedging", 0.5),
            KeywordWeight("arbitrage", 0.5),
            KeywordWeight("backtest", 0.5),
        ],
        context_keywords=[
            KeywordWeight("model", 0.2),
            KeywordWeight("strategy", 0.1),
        ],
        min_score=0.3,
    ),
    "machine_learning": MethodologyProfile(
        category="machine_learning",
        primary_keywords=[
            KeywordWeight("machine learning", 1.0),
            KeywordWeight("deep learning", 1.0),
            KeywordWeight("neural network", 1.0),
        ],
        secondary_keywords=[
            KeywordWeight("classification", 0.5),
            KeywordWeight("regression", 0.4),
            KeywordWeight("random forest", 0.7),
            KeywordWeight("gradient boosting", 0.7),
            KeywordWeight("lstm", 0.7),
            KeywordWeight("transformer", 0.6),
            KeywordWeight("feature engineering", 0.5),
            KeywordWeight("training data", 0.5),
            KeywordWeight("overfitting", 0.5),
            KeywordWeight("cross validation", 0.5),
            KeywordWeight("prediction", 0.3),
        ],
        context_keywords=[
            KeywordWeight("model", 0.2),
            KeywordWeight("data", 0.1),
        ],
        min_score=0.35,
    ),
    "risk_management": MethodologyProfile(
        category="risk_management",
        primary_keywords=[
            KeywordWeight("risk management", 1.0),
            KeywordWeight("position sizing", 1.0),
            KeywordWeight("risk control", 0.9),
        ],
        secondary_keywords=[
            KeywordWeight("stop loss", 0.7),
            KeywordWeight("take profit", 0.6),
            KeywordWeight("risk reward", 0.7),
            KeywordWeight("drawdown", 0.5),
            KeywordWeight("max drawdown", 0.6),
            KeywordWeight("portfolio risk", 0.7),
            KeywordWeight("kelly criterion", 0.7),
            KeywordWeight("fixed fractional", 0.6),
            KeywordWeight("position size", 0.7),
            KeywordWeight("risk per trade", 0.7),
            KeywordWeight("exposure", 0.4),
            KeywordWeight("hedging", 0.5),
        ],
        context_keywords=[
            KeywordWeight("trade", 0.2),
            KeywordWeight("capital", 0.2),
        ],
        min_score=0.3,
    ),
}


class MethodologyTag(BaseModel):
    model_config = ConfigDict(extra="forbid")
    category: MethodologyCategory
    confidence: float = Field(ge=0.0, le=1.0, default=1.0)
    evidence: list[str] = Field(default_factory=list)
    notes: str = ""


@dataclass
class ClassificationResult:
    category: str
    confidence: float
    evidence: list[str]
    scores: dict[str, float]


def _score_methodology(text: str, profile: MethodologyProfile) -> tuple[float, list[str]]:
    text_lower = text.lower()
    score = 0.0
    evidence: list[str] = []

    for kw in profile.primary_keywords:
        if kw.case_sensitive:
            if kw.keyword in text:
                score += kw.weight
                evidence.append(kw.keyword)
        else:
            if kw.keyword.lower() in text_lower:
                score += kw.weight
                evidence.append(kw.keyword)

    for kw in profile.secondary_keywords:
        if kw.case_sensitive:
            if kw.keyword in text:
                score += kw.weight * 0.7
                evidence.append(kw.keyword)
        else:
            if kw.keyword.lower() in text_lower:
                score += kw.weight * 0.7
                evidence.append(kw.keyword)

    for kw in profile.context_keywords:
        if kw.case_sensitive:
            if kw.keyword in text:
                score += kw.weight * 0.3
                evidence.append(kw.keyword)
        else:
            if kw.keyword.lower() in text_lower:
                score += kw.weight * 0.3
                evidence.append(kw.keyword)

    return score, evidence


def classify_methodology_context(
    text: str,
    context: str = "",
) -> ClassificationResult:
    combined = f"{context} {text}" if context else text
    all_scores: dict[str, float] = {}
    all_evidence: dict[str, list[str]] = {}

    for cat, profile in PROFILES.items():
        score, evidence = _score_methodology(combined, profile)
        all_scores[cat] = score
        all_evidence[cat] = evidence

    result_cat: str = "unknown"
    best_score = 0.0
    best_evidence: list[str] = []

    for key, score in all_scores.items():
        profile = PROFILES[key]
        if score >= profile.min_score and score > best_score:
            result_cat = key
            best_score = score
            best_evidence = all_evidence[key]

    max_possible = 2.0
    confidence = min(best_score / max_possible, 1.0) if best_score > 0 else 0.0

    return ClassificationResult(
        category=result_cat,
        confidence=round(confidence, 3),
        evidence=best_evidence,
        scores=all_scores,
    )


def classify_methodology(text: str) -> str:
    result = classify_methodology_context(text)
    return result.category


def list_categories() -> list[str]:
    return sorted(METHODOLOGY_TAXONOMY.keys())
