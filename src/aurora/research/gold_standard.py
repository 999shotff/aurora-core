"""Gold-standard benchmark for controlled LLM extraction experiment.

Manually curated examples with expected outputs.
Small, high-quality dataset covering all methodologies.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class BenchmarkCase:
    case_id: str
    text: str
    document_id: str = "bench_001"
    page_number: int = 1
    source_file: str = "benchmark.pdf"
    is_ocr: bool = False
    expected_claims: list[dict] = field(default_factory=list)
    expected_methodology: str = "unknown"
    expected_claim_type: str = "unknown"
    category_group: str = "unknown"
    notes: str = ""


GOLD_STANDARD_CASES: list[BenchmarkCase] = [
    # Fibonacci
    BenchmarkCase(
        case_id="fib_001",
        text="The 0.618 fibonacci retracement level acts as strong support in uptrends, "
             "and traders often enter long positions when price bounces from this level.",
        expected_methodology="fibonacci",
        expected_claim_type="rule",
        category_group="fibonacci",
        expected_claims=[{
            "exact_source_text": "The 0.618 fibonacci retracement level acts as strong support in uptrends",
            "claim_type": "rule",
            "methodology": "fibonacci",
            "condition": "price bounces from 0.618 fibonacci retracement",
            "expected_effect": "enter long position",
        }],
    ),
    BenchmarkCase(
        case_id="fib_002",
        text="Fibonacci extensions at 1.618 and 2.618 project profit targets "
             "for swing traders following impulse waves.",
        expected_methodology="fibonacci",
        expected_claim_type="observation",
        category_group="fibonacci",
    ),
    # Gann
    BenchmarkCase(
        case_id="gann_001",
        text="The Gann 1x1 angle line provides dynamic support throughout the trend, "
             "and price respect for this angle confirms the trend integrity.",
        expected_methodology="gann",
        expected_claim_type="observation",
        category_group="gann",
    ),
    BenchmarkCase(
        case_id="gann_002",
        text="W.D. Gann's law of vibration states that stocks move in predictable cycles "
             "governed by mathematical and geometric relationships.",
        expected_methodology="gann",
        expected_claim_type="definition",
        category_group="gann",
    ),
    # Liquidity
    BenchmarkCase(
        case_id="liq_001",
        text="A liquidity sweep occurs when price temporarily breaks below support "
             "to trigger stop losses before reversing sharply upward.",
        expected_methodology="liquidity",
        expected_claim_type="definition",
        category_group="liquidity",
    ),
    BenchmarkCase(
        case_id="liq_002",
        text="Order blocks form where institutional traders place large orders, "
             "creating zones of significant supply and demand.",
        expected_methodology="liquidity",
        expected_claim_type="definition",
        category_group="liquidity",
    ),
    # Technical Analysis
    BenchmarkCase(
        case_id="ta_001",
        text="When RSI drops below 30, the asset is considered oversold and likely to bounce. "
             "Traders often use this as a buying signal in ranging markets.",
        expected_methodology="technical_analysis",
        expected_claim_type="rule",
        category_group="technical_analysis",
    ),
    BenchmarkCase(
        case_id="ta_002",
        text="The 200-day moving average serves as a major dynamic support level "
             "for the broader market index.",
        expected_methodology="technical_analysis",
        expected_claim_type="observation",
        category_group="technical_analysis",
    ),
    # Volatility
    BenchmarkCase(
        case_id="vol_001",
        text="Implied volatility tends to expand ahead of earnings announcements "
             "and contract afterward, creating a volatility crush.",
        expected_methodology="volatility",
        expected_claim_type="observation",
        category_group="volatility",
    ),
    BenchmarkCase(
        case_id="vol_002",
        text="ATR-based position sizing adjusts trade size inversely to volatility, "
             "ensuring consistent risk per trade across different market conditions.",
        expected_methodology="volatility",
        expected_claim_type="rule",
        category_group="volatility",
    ),
    # Market Psychology
    BenchmarkCase(
        case_id="psych_001",
        text="Fear and greed drive most market participants to buy high and sell low, "
             "creating opportunities for disciplined contrarian traders.",
        expected_methodology="market_psychology",
        expected_claim_type="observation",
        category_group="market_psychology",
    ),
    # News
    BenchmarkCase(
        case_id="news_001",
        text="Non-farm payroll releases cause significant intraday price movements "
             "as traders adjust positions based on employment data.",
        expected_methodology="news",
        expected_claim_type="observation",
        category_group="news",
    ),
    # Astrology
    BenchmarkCase(
        case_id="astro_001",
        text="Mercury retrograde periods correlate with increased market turbulence "
             "and uncertain price action across multiple asset classes.",
        expected_methodology="astrology",
        expected_claim_type="observation",
        category_group="astrology",
    ),
    # Time Cycles
    BenchmarkCase(
        case_id="cycle_001",
        text="The dominant 40-week cycle identifies major market turning points, "
             "with cycle lows often marking significant buying opportunities.",
        expected_methodology="time_cycles",
        expected_claim_type="observation",
        category_group="time_cycles",
    ),
    # Elliott Wave
    BenchmarkCase(
        case_id="elliott_001",
        text="An impulse wave consists of five sub-waves in the direction of the larger trend, "
             "followed by a three-wave corrective pattern.",
        expected_methodology="elliott_wave",
        expected_claim_type="definition",
        category_group="elliott_wave",
    ),
    # Quantitative Finance
    BenchmarkCase(
        case_id="quant_001",
        text="The Sharpe ratio measures risk-adjusted return by dividing excess return "
             "by the standard deviation of returns.",
        expected_methodology="quantitative_finance",
        expected_claim_type="definition",
        category_group="quantitative_finance",
    ),
    # Risk Management
    BenchmarkCase(
        case_id="risk_001",
        text="The Kelly criterion determines optimal position size by maximizing "
             "the expected growth rate of capital.",
        expected_methodology="risk_management",
        expected_claim_type="definition",
        category_group="risk_management",
    ),
    # Non-claim text
    BenchmarkCase(
        case_id="non_001",
        text="The weather forecast predicts rain for the next three days "
             "with temperatures dropping to seasonal averages.",
        expected_methodology="unknown",
        expected_claim_type="unknown",
        category_group="unknown",
        notes="Non-financial text, should not extract claims",
    ),
    # Ambiguous text
    BenchmarkCase(
        case_id="amb_001",
        text="The market moved up today on higher volume than yesterday.",
        expected_methodology="unknown",
        expected_claim_type="unknown",
        category_group="unknown",
        notes="Factual observation, not a tradeable claim",
    ),
    # Volume
    BenchmarkCase(
        case_id="vol_analysis_001",
        text="Volume divergence at swing highs warns of distribution "
             "and potential trend reversal.",
        expected_methodology="volume",
        expected_claim_type="observation",
        category_group="volume",
    ),
    # VWAP
    BenchmarkCase(
        case_id="vwap_001",
        text="Price reversion to VWAP is a common intraday setup "
             "where mean-reversion traders enter positions.",
        expected_methodology="vwap",
        expected_claim_type="observation",
        category_group="vwap",
    ),
    # Order Flow
    BenchmarkCase(
        case_id="of_001",
        text="Cumulative delta divergence at support levels signals absorption "
             "and potential bullish reversal.",
        expected_methodology="order_flow",
        expected_claim_type="observation",
        category_group="order_flow",
    ),
    # Market Profile
    BenchmarkCase(
        case_id="mp_001",
        text="The point of control represents the price level with the most time spent, "
             "acting as a fair value reference for the session.",
        expected_methodology="market_profile",
        expected_claim_type="definition",
        category_group="market_profile",
    ),
    # Market Structure
    BenchmarkCase(
        case_id="ms_001",
        text="A break of structure occurs when price violates a previous swing high or low, "
             "indicating a potential trend change.",
        expected_methodology="market_structure",
        expected_claim_type="definition",
        category_group="market_structure",
    ),
    # Machine Learning
    BenchmarkCase(
        case_id="ml_001",
        text="LSTM neural networks capture temporal dependencies in sequential price data "
             "for pattern recognition tasks.",
        expected_methodology="machine_learning",
        expected_claim_type="observation",
        category_group="machine_learning",
    ),
]


def get_gold_standard() -> list[BenchmarkCase]:
    return GOLD_STANDARD_CASES


def get_gold_standard_by_group() -> dict[str, list[BenchmarkCase]]:
    groups: dict[str, list[BenchmarkCase]] = {}
    for case in GOLD_STANDARD_CASES:
        groups.setdefault(case.category_group, []).append(case)
    return groups
