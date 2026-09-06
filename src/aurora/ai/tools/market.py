"""
Market tools for LLM-2 grounded intelligence.

Wraps existing aurora.features.market_context into bounded tool operations.
All tools are READ-only and deterministic.
"""

from __future__ import annotations

from typing import Any

from aurora.ai.tools.base import AITool, ToolPermission, ToolResult


class GetMarketDataTool(AITool):
    """Retrieve OHLCV market data for a symbol."""

    @property
    def name(self) -> str:
        return "market.get_ohlcv"

    @property
    def description(self) -> str:
        return "Get OHLCV price data for a financial instrument"

    @property
    def required_permissions(self) -> list[ToolPermission]:
        return [ToolPermission.READ_MARKET]

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "Ticker symbol (e.g., AAPL)"},
                "period": {
                    "type": "string",
                    "enum": ["1d", "5d", "1mo", "3mo", "6mo", "1y", "2y", "5y"],
                    "description": "Data period",
                },
                "interval": {
                    "type": "string",
                    "enum": ["1d", "1wk", "1mo"],
                    "description": "Data interval",
                },
            },
            "required": ["symbol"],
        }

    def _execute(self, parameters: dict[str, Any]) -> ToolResult:
        symbol = parameters["symbol"].upper()
        period = parameters.get("period", "3mo")
        interval = parameters.get("interval", "1d")

        try:
            from aurora.features.market_context import MarketContext

            ctx = MarketContext()
            ohlcv = ctx.get_ohlcv(symbol, period=period, interval=interval)

            if ohlcv is None or ohlcv.empty:
                return ToolResult(
                    tool_name=self.name,
                    status="error",
                    data={"symbol": symbol, "period": period, "interval": interval},
                    evidence_id="",
                    execution_time_ms=0.0,
                    error=f"No data available for {symbol}",
                )

            data = {
                "symbol": symbol,
                "period": period,
                "interval": interval,
                "rows": len(ohlcv),
                "latest_close": float(ohlcv["Close"].iloc[-1])
                if "Close" in ohlcv.columns
                else None,
                "latest_date": str(ohlcv.index[-1])
                if len(ohlcv) > 0
                else None,
                "min_close": float(ohlcv["Close"].min())
                if "Close" in ohlcv.columns
                else None,
                "max_close": float(ohlcv["Close"].max())
                if "Close" in ohlcv.columns
                else None,
                "source": "yfinance",
            }

            return ToolResult(
                tool_name=self.name,
                status="success",
                data=data,
                evidence_id=self._compute_evidence_id(data),
                execution_time_ms=0.0,
                source_refs=[f"yfinance:{symbol}:{period}:{interval}"],
            )
        except Exception as exc:
            return ToolResult(
                tool_name=self.name,
                status="error",
                data={"symbol": symbol},
                evidence_id="",
                execution_time_ms=0.0,
                error=str(exc),
            )


class GetMarketAnalysisTool(AITool):
    """Run deterministic technical analysis on a symbol."""

    @property
    def name(self) -> str:
        return "market.get_analysis"

    @property
    def description(self) -> str:
        return "Run deterministic technical analysis (RSI, MACD, Bollinger, support/resistance)"

    @property
    def required_permissions(self) -> list[ToolPermission]:
        return [ToolPermission.READ_MARKET, ToolPermission.RUN_DETERMINISTIC_ANALYSIS]

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "period": {"type": "string", "default": "3mo"},
            },
            "required": ["symbol"],
        }

    def _execute(self, parameters: dict[str, Any]) -> ToolResult:
        symbol = parameters["symbol"].upper()
        period = parameters.get("period", "3mo")

        try:
            from aurora.features.market_context import MarketContext

            ctx = MarketContext()
            analysis = ctx.analyze(symbol, period=period)

            if analysis is None:
                return ToolResult(
                    tool_name=self.name,
                    status="error",
                    data={"symbol": symbol},
                    evidence_id="",
                    execution_time_ms=0.0,
                    error=f"Analysis unavailable for {symbol}",
                )

            data = {
                "symbol": symbol,
                "period": period,
                "indicators": {}
                if not hasattr(analysis, "indicators")
                else analysis.indicators,
                "signals": []
                if not hasattr(analysis, "signals")
                else analysis.signals,
                "support_levels": []
                if not hasattr(analysis, "support_levels")
                else analysis.support_levels,
                "resistance_levels": []
                if not hasattr(analysis, "resistance_levels")
                else analysis.resistance_levels,
                "source": "deterministic_analysis",
            }

            return ToolResult(
                tool_name=self.name,
                status="success",
                data=data,
                evidence_id=self._compute_evidence_id(data),
                execution_time_ms=0.0,
                evidence_type="analysis",
                source_refs=[f"analysis:{symbol}:{period}"],
            )
        except Exception as exc:
            return ToolResult(
                tool_name=self.name,
                status="error",
                data={"symbol": symbol},
                evidence_id="",
                execution_time_ms=0.0,
                error=str(exc),
            )


class MarketSentimentTool(AITool):
    """Aggregate sentiment from available news/social sources."""

    @property
    def name(self) -> str:
        return "market.sentiment"

    @property
    def description(self) -> str:
        return "Get aggregated market sentiment for a symbol"

    @property
    def required_permissions(self) -> list[ToolPermission]:
        return [ToolPermission.READ_MARKET]

    def input_schema(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "lookback_hours": {
                    "type": "integer",
                    "default": 24,
                    "minimum": 1,
                    "maximum": 168,
                },
            },
            "required": ["symbol"],
        }

    def _execute(self, parameters: dict[str, Any]) -> ToolResult:
        symbol = parameters["symbol"].upper()
        lookback = parameters.get("lookback_hours", 24)

        # Deterministic sentiment aggregation from available sources
        data = {
            "symbol": symbol,
            "lookback_hours": lookback,
            "sentiment_score": None,  # No fabricated data
            "data_available": False,
            "reason": "No live sentiment data source connected",
            "source": "sentiment_aggregator",
        }

        return ToolResult(
            tool_name=self.name,
            status="success",
            data=data,
            evidence_id=self._compute_evidence_id(data),
            execution_time_ms=0.0,
            evidence_type="observation",
            source_refs=[f"sentiment:{symbol}"],
        )


# ── Exported Tool List ─────────────────────────────────────────────────────

MARKET_TOOLS: list[AITool] = [
    GetMarketDataTool(),
    GetMarketAnalysisTool(),
    MarketSentimentTool(),
]
