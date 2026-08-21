"""Phase 4.5 — Curated classification benchmark.

Manually curated test corpus for evaluating the deterministic classifier.
Contains synthetic examples for each methodology.
Expected classifications are explicitly defined.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class BenchmarkCase:
    text: str
    expected_methodology: str
    description: str
    category_group: str


BENCHMARK_CASES: list[BenchmarkCase] = [
    # Fibonacci
    BenchmarkCase(
        text="The 0.618 fibonacci retracement level acts as strong support in uptrends.",
        expected_methodology="fibonacci",
        description="Fibonacci retracement level",
        category_group="fibonacci",
    ),
    BenchmarkCase(
        text="Price bounced perfectly at the 38.2% fibonacci extension target.",
        expected_methodology="fibonacci",
        description="Fibonacci extension target",
        category_group="fibonacci",
    ),
    BenchmarkCase(
        text="The golden ratio 1.618 fibonacci level determines the next resistance zone.",
        expected_methodology="fibonacci",
        description="Golden ratio fibonacci",
        category_group="fibonacci",
    ),
    BenchmarkCase(
        text="Fibonacci time zones project the next major turning point in the market cycle.",
        expected_methodology="fibonacci",
        description="Fibonacci time zones",
        category_group="fibonacci",
    ),

    # Gann
    BenchmarkCase(
        text="The Gann angle 1x1 line provides dynamic support throughout the trend.",
        expected_methodology="gann",
        description="Gann angle support",
        category_group="gann",
    ),
    BenchmarkCase(
        text="Gann square of 9 calculations project the next resistance level.",
        expected_methodology="gann",
        description="Gann square of 9",
        category_group="gann",
    ),
    BenchmarkCase(
        text="W.D. Gann's law of vibration governs the natural rhythm of price movements.",
        expected_methodology="gann",
        description="Gann law of vibration",
        category_group="gann",
    ),
    BenchmarkCase(
        text="The Gann fan lines at 45 degree angles define the trend structure.",
        expected_methodology="gann",
        description="Gann fan lines",
        category_group="gann",
    ),

    # Liquidity
    BenchmarkCase(
        text="The liquidity sweep grabbed stops below the equal lows before reversing.",
        expected_methodology="liquidity",
        description="Liquidity sweep stops",
        category_group="liquidity",
    ),
    BenchmarkCase(
        text="Smart money accumulated at the order block before the markup phase.",
        expected_methodology="liquidity",
        description="Order block accumulation",
        category_group="liquidity",
    ),
    BenchmarkCase(
        text="The break of structure confirmed the change of character from bullish to bearish.",
        expected_methodology="market_structure",
        description="BOS and CHoCH",
        category_group="liquidity",
    ),
    BenchmarkCase(
        text="Sell side liquidity pools resting below the recent swing lows were targeted.",
        expected_methodology="liquidity",
        description="Sell side liquidity",
        category_group="liquidity",
    ),

    # Technical Analysis
    BenchmarkCase(
        text="The 200-day moving average acts as a major support level for the index.",
        expected_methodology="technical_analysis",
        description="Moving average support",
        category_group="technical_analysis",
    ),
    BenchmarkCase(
        text="RSI divergence at the swing high signaled a potential reversal.",
        expected_methodology="technical_analysis",
        description="RSI divergence",
        category_group="technical_analysis",
    ),
    BenchmarkCase(
        text="The cup and handle chart pattern broke out above the neckline with volume confirmation.",
        expected_methodology="technical_analysis",
        description="Chart pattern breakout",
        category_group="technical_analysis",
    ),
    BenchmarkCase(
        text="MACD crossover above the signal line confirmed bullish momentum.",
        expected_methodology="technical_analysis",
        description="MACD crossover",
        category_group="technical_analysis",
    ),

    # Volatility
    BenchmarkCase(
        text="Implied volatility expanded significantly ahead of the earnings announcement.",
        expected_methodology="volatility",
        description="Implied volatility expansion",
        category_group="volatility",
    ),
    BenchmarkCase(
        text="ATR-based volatility stop placement ensures adequate risk per trade.",
        expected_methodology="volatility",
        description="ATR-based stops",
        category_group="volatility",
    ),
    BenchmarkCase(
        text="The volatility regime shifted from low to high compression range.",
        expected_methodology="volatility",
        description="Volatility regime shift",
        category_group="volatility",
    ),
    BenchmarkCase(
        text="Bollinger bands squeeze indicates impending volatility breakout.",
        expected_methodology="volatility",
        description="Bollinger band squeeze",
        category_group="volatility",
    ),

    # Market Psychology
    BenchmarkCase(
        text="Fear and greed indices reached extreme greed levels at the market top.",
        expected_methodology="market_psychology",
        description="Fear and greed sentiment",
        category_group="market_psychology",
    ),
    BenchmarkCase(
        text="Cognitive bias leads traders to hold losing positions too long.",
        expected_methodology="market_psychology",
        description="Cognitive bias in trading",
        category_group="market_psychology",
    ),
    BenchmarkCase(
        text="Crowd psychology drives panic selling during market crashes.",
        expected_methodology="market_psychology",
        description="Crowd psychology panic",
        category_group="market_psychology",
    ),

    # News
    BenchmarkCase(
        text="Non-farm payroll releases cause significant intraday price movements.",
        expected_methodology="news",
        description="NFP news impact",
        category_group="news",
    ),
    BenchmarkCase(
        text="FOMC interest rate decisions are the most market-moving events.",
        expected_methodology="news",
        description="FOMC event impact",
        category_group="news",
    ),
    BenchmarkCase(
        text="Earnings surprises drive gap moves in individual stock prices.",
        expected_methodology="news",
        description="Earnings surprise impact",
        category_group="news",
    ),

    # Astrology
    BenchmarkCase(
        text="Mercury retrograde periods correlate with increased market turbulence and uncertainty.",
        expected_methodology="astrology",
        description="Mercury retrograde correlation",
        category_group="astrology",
    ),
    BenchmarkCase(
        text="Planetary alignment between Jupiter and Saturn marks major cycle turns.",
        expected_methodology="astrology",
        description="Planetary alignment cycles",
        category_group="astrology",
    ),
    BenchmarkCase(
        text="Lunar eclipse dates coincide with significant market reversals.",
        expected_methodology="astrology",
        description="Lunar eclipse reversals",
        category_group="astrology",
    ),

    # Time Cycles
    BenchmarkCase(
        text="The dominant 40-week cycle identifies major market turning points.",
        expected_methodology="time_cycles",
        description="Dominant cycle analysis",
        category_group="time_cycles",
    ),
    BenchmarkCase(
        text="Seasonal patterns show September is historically the weakest month.",
        expected_methodology="time_cycles",
        description="Seasonal pattern",
        category_group="time_cycles",
    ),
    BenchmarkCase(
        text="Hurst cycle analysis projects the next cycle low in 120 days.",
        expected_methodology="time_cycles",
        description="Hurst cycle projection",
        category_group="time_cycles",
    ),

    # Elliott Wave
    BenchmarkCase(
        text="The impulse wave structure consists of 5 waves in the direction of the trend.",
        expected_methodology="elliott_wave",
        description="Impulse wave structure",
        category_group="elliott_wave",
    ),
    BenchmarkCase(
        text="The corrective A-B-C pattern retraces to the 61.8% level before continuing the trend.",
        expected_methodology="elliott_wave",
        description="Corrective wave pattern",
        category_group="elliott_wave",
    ),
    BenchmarkCase(
        text="Elliott wave 3 is typically the longest and strongest wave in the sequence.",
        expected_methodology="elliott_wave",
        description="Wave 3 characteristics",
        category_group="elliott_wave",
    ),

    # Volume
    BenchmarkCase(
        text="Volume divergence at the swing high warned of distribution.",
        expected_methodology="volume",
        description="Volume divergence warning",
        category_group="volume",
    ),
    BenchmarkCase(
        text="OBV divergence confirmed the underlying trend strength.",
        expected_methodology="volume",
        description="OBV divergence confirmation",
        category_group="volume",
    ),

    # Order Flow
    BenchmarkCase(
        text="Cumulative delta divergence signaled absorption at the support level.",
        expected_methodology="order_flow",
        description="Cumulative delta divergence",
        category_group="order_flow",
    ),
    BenchmarkCase(
        text="Footprint charts reveal aggressive buying at the bid-ask spread.",
        expected_methodology="order_flow",
        description="Footprint chart analysis",
        category_group="order_flow",
    ),

    # VWAP
    BenchmarkCase(
        text="Price reversion to VWAP is a common intraday trading setup.",
        expected_methodology="vwap",
        description="VWAP reversion",
        category_group="vwap",
    ),
    BenchmarkCase(
        text="VWAP deviation bands provide dynamic support and resistance levels.",
        expected_methodology="vwap",
        description="VWAP deviation bands",
        category_group="vwap",
    ),

    # Quantitative Finance
    BenchmarkCase(
        text="The Sharpe ratio measures risk-adjusted return of the portfolio.",
        expected_methodology="quantitative_finance",
        description="Sharpe ratio metric",
        category_group="quantitative_finance",
    ),
    BenchmarkCase(
        text="Monte Carlo simulation generates probability distributions for portfolio outcomes.",
        expected_methodology="quantitative_finance",
        description="Monte Carlo simulation",
        category_group="quantitative_finance",
    ),
    BenchmarkCase(
        text="Mean variance optimization constructs the efficient frontier.",
        expected_methodology="quantitative_finance",
        description="Mean variance optimization",
        category_group="quantitative_finance",
    ),

    # Risk Management
    BenchmarkCase(
        text="Position sizing with 1% risk per trade limits maximum drawdown exposure.",
        expected_methodology="risk_management",
        description="Position sizing risk",
        category_group="risk_management",
    ),
    BenchmarkCase(
        text="The Kelly criterion determines optimal bet size for maximum growth.",
        expected_methodology="risk_management",
        description="Kelly criterion sizing",
        category_group="risk_management",
    ),
    BenchmarkCase(
        text="Position sizing based on risk per trade protects against excessive drawdown.",
        expected_methodology="risk_management",
        description="Risk per trade sizing",
        category_group="risk_management",
    ),

    # Machine Learning
    BenchmarkCase(
        text="LSTM neural networks capture temporal dependencies in price data.",
        expected_methodology="machine_learning",
        description="LSTM neural network",
        category_group="machine_learning",
    ),
    BenchmarkCase(
        text="Random forest classification predicts regime changes in the market.",
        expected_methodology="machine_learning",
        description="Random forest classification",
        category_group="machine_learning",
    ),

    # Unknown / Non-financial
    BenchmarkCase(
        text="The weather forecast predicts rain for the next three days.",
        expected_methodology="unknown",
        description="Weather forecast (non-financial)",
        category_group="unknown",
    ),
    BenchmarkCase(
        text="The restaurant serves Italian cuisine with fresh ingredients.",
        expected_methodology="unknown",
        description="Restaurant review (non-financial)",
        category_group="unknown",
    ),
    BenchmarkCase(
        text="The stock split will be effective from next Monday onward.",
        expected_methodology="unknown",
        description="Stock split announcement (factual, not methodology)",
        category_group="unknown",
    ),
]


def get_benchmark_cases() -> list[BenchmarkCase]:
    return BENCHMARK_CASES


def get_benchmark_by_group() -> dict[str, list[BenchmarkCase]]:
    groups: dict[str, list[BenchmarkCase]] = {}
    for case in BENCHMARK_CASES:
        groups.setdefault(case.category_group, []).append(case)
    return groups
