"""M29 Backtest Engine Tests.

39 tests covering:
- Data model (Bar, Dataset, Provenance, QualityReport)
- Strategy interface (Signal validation, StrategyConfig)
- Position tracking (open, close, PnL calculation)
- Transaction costs (NoCost, Fixed, Slippage models)
- Performance metrics (equity curve, drawdowns, Sharpe)
- Risk metrics (VaR, CVaR, ulcer index)
- Backtest engine (end-to-end, strategy execution)
- Leakage prevention (no future data in strategy)
- Edge cases (empty dataset, zero equity, flat market)
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import isclose

import pytest

from aurora.research.backtest.data_model import (
    Bar,
    Dataset,
    DatasetMetadata,
    Provenance,
    QualityGrade,
    QualityReport,
)
from aurora.research.backtest.strategy import (
    Signal,
    Side,
    StrategyConfig,
)
from aurora.research.backtest.position import (
    Fill,
    PositionSide,
    PositionTracker,
    Trade,
)
from aurora.research.backtest.costs import (
    CostBreakdown,
    FixedCostModel,
    NoCostModel,
    SlippageModel,
)
from aurora.research.backtest.metrics import (
    PerformanceMetrics,
    compute_metrics,
)
from aurora.research.backtest.risk import (
    RiskMetrics,
    compute_risk_metrics,
)
from aurora.research.backtest.engine import (
    BacktestEngine,
    BacktestResult,
)


# ── Helpers ──

NOW = datetime(2025, 6, 1, tzinfo=timezone.utc)


def _bar(
    ts: datetime,
    o: float = 100.0,
    h: float = 102.0,
    l: float = 98.0,
    c: float = 101.0,
    v: float = 1_000_000.0,
) -> Bar:
    return Bar(timestamp=ts, open=o, high=h, low=l, close=c, volume=v)


def _make_bars(n: int = 50, start_price: float = 100.0) -> list[Bar]:
    bars = []
    price = start_price
    for i in range(n):
        ts = NOW + timedelta(days=i)
        o = price
        c = price * (1.01 if i % 3 == 0 else 0.99)
        h = max(o, c) * 1.005
        l = min(o, c) * 0.995
        bars.append(_bar(ts, o, h, l, c))
        price = c
    return bars


def _dataset(bars: list[Bar] | None = None) -> Dataset:
    if bars is None:
        bars = _make_bars()
    return Dataset(
        bars=bars,
        provenance=Provenance(source="test", symbol="TEST", frequency="daily", total_bars=len(bars)),
        metadata=DatasetMetadata(name="test"),
        quality=QualityReport(total_bars=len(bars)),
    )


class _AlwaysFlatStrategy:
    _config = StrategyConfig(name="flat", lookback=0)

    def config(self) -> StrategyConfig:
        return self._config

    def on_start(self, dataset: Dataset) -> None:
        pass

    def on_end(self) -> None:
        pass

    def on_bar(self, bar: Bar, history: list[Bar], position: float, equity: float) -> Signal:
        return Signal(side=Side.FLAT)


class _AlwaysLongStrategy:
    _config = StrategyConfig(name="always_long", lookback=0)

    def config(self) -> StrategyConfig:
        return self._config

    def on_start(self, dataset: Dataset) -> None:
        pass

    def on_end(self) -> None:
        pass

    def on_bar(self, bar: Bar, history: list[Bar], position: float, equity: float) -> Signal:
        if position == 0:
            return Signal(side=Side.LONG, strength=1.0)
        return Signal(side=Side.FLAT)


class _FlipFlopStrategy:
    _config = StrategyConfig(name="flip_flop", lookback=0)
    _turn = 0

    def config(self) -> StrategyConfig:
        return self._config

    def on_start(self, dataset: Dataset) -> None:
        self._turn = 0

    def on_end(self) -> None:
        pass

    def on_bar(self, bar: Bar, history: list[Bar], position: float, equity: float) -> Signal:
        self._turn += 1
        if position == 0:
            return Signal(side=Side.LONG, strength=1.0)
        if self._turn % 5 == 0:
            return Signal(side=Side.FLAT)
        return Signal(side=Side.FLAT)


class _NoFutureStrategy:
    """Strategy that only looks at historical bars — no future leakage."""
    _config = StrategyConfig(name="no_future", lookback=10)
    _seen_timestamps: list[datetime] = []

    def config(self) -> StrategyConfig:
        return self._config

    def on_start(self, dataset: Dataset) -> None:
        self._seen_timestamps = []

    def on_end(self) -> None:
        pass

    def on_bar(self, bar: Bar, history: list[Bar], position: float, equity: float) -> Signal:
        self._seen_timestamps.append(bar.timestamp)
        for h in history:
            assert h.timestamp < bar.timestamp, (
                f"LEAKAGE: history bar {h.timestamp} >= current {bar.timestamp}"
            )
        return Signal(side=Side.FLAT)


# ── Data Model Tests ──


class TestBar:
    def test_valid_bar(self):
        b = Bar(timestamp=NOW, open=100, high=102, low=98, close=101)
        assert b.close == 101

    def test_high_must_be_gte_low(self):
        with pytest.raises(ValueError, match="high.*must be >= low"):
            Bar(timestamp=NOW, open=100, high=95, low=100, close=101)

    def test_negative_price_rejected(self):
        with pytest.raises(ValueError, match="non-negative"):
            Bar(timestamp=NOW, open=-1, high=102, low=98, close=101)

    def test_zero_volume_allowed(self):
        b = Bar(timestamp=NOW, open=100, high=102, low=98, close=101, volume=0)
        assert b.volume == 0

    def test_indicators_dict(self):
        b = Bar(timestamp=NOW, open=100, high=102, low=98, close=101, indicators={"rsi": 65.0})
        assert b.indicators["rsi"] == 65.0


class TestDataset:
    def test_count(self):
        ds = _dataset(_make_bars(10))
        assert ds.count == 10

    def test_start_end(self):
        bars = _make_bars(5)
        ds = _dataset(bars)
        assert ds.start == bars[0].timestamp
        assert ds.end == bars[-1].timestamp

    def test_empty_dataset(self):
        ds = Dataset(
            bars=[],
            provenance=Provenance(source="test", symbol="X", frequency="daily", total_bars=0),
            metadata=DatasetMetadata(name="empty"),
            quality=QualityReport(total_bars=0),
        )
        assert ds.count == 0
        assert ds.start is None

    def test_get_bar(self):
        bars = _make_bars(5)
        ds = _dataset(bars)
        found = ds.get_bar(bars[2].timestamp)
        assert found is not None
        assert found.timestamp == bars[2].timestamp

    def test_get_bar_missing(self):
        ds = _dataset(_make_bars(5))
        assert ds.get_bar(datetime(2099, 1, 1, tzinfo=timezone.utc)) is None

    def test_slice(self):
        bars = _make_bars(10)
        ds = _dataset(bars)
        sliced = ds.slice(start=bars[3].timestamp, end=bars[7].timestamp)
        assert len(sliced) == 5
        assert sliced[0].timestamp == bars[3].timestamp

    def test_validate_chronological(self):
        ds = _dataset(_make_bars(10))
        errors = ds.validate_chronological()
        assert errors == []

    def test_validate_chronological_fail(self):
        bars = _make_bars(5)
        # Swap two bars to create out-of-order
        bars_list = list(bars)
        bars_list[1], bars_list[3] = bars_list[3], bars_list[1]
        ds = Dataset(
            bars=bars_list,
            provenance=Provenance(source="test", symbol="X", frequency="daily", total_bars=5),
            metadata=DatasetMetadata(name="bad"),
            quality=QualityReport(total_bars=5),
        )
        errors = ds.validate_chronological()
        assert len(errors) > 0


class TestProvenance:
    def test_negative_bars_rejected(self):
        with pytest.raises(ValueError, match="non-negative"):
            Provenance(source="x", symbol="X", frequency="daily", total_bars=-1)


class TestQualityReport:
    def test_quality_score_perfect(self):
        q = QualityReport(total_bars=100)
        assert q.quality_score == 1.0

    def test_quality_score_with_errors(self):
        q = QualityReport(total_bars=100, missing_ohlc=10, negative_prices=5)
        assert 0.0 < q.quality_score < 1.0

    def test_quality_score_empty(self):
        q = QualityReport(total_bars=0)
        assert q.quality_score == 0.0


# ── Signal Tests ──


class TestSignal:
    def test_valid_long(self):
        s = Signal(side=Side.LONG, strength=0.5)
        assert s.side == Side.LONG

    def test_valid_flat(self):
        s = Signal(side=Side.FLAT)
        assert s.side == Side.FLAT

    def test_strength_out_of_range(self):
        with pytest.raises(ValueError, match="strength"):
            Signal(side=Side.LONG, strength=1.5)

    def test_long_stop_loss_must_be_below_take_profit(self):
        with pytest.raises(ValueError, match="stop_loss.*must be < take_profit"):
            Signal(side=Side.LONG, stop_loss=110, take_profit=100)


# ── Position Tests ──


class TestPositionTracker:
    def test_initially_flat(self):
        t = PositionTracker()
        assert t.is_flat

    def test_open_long(self):
        t = PositionTracker()
        fill = Fill(timestamp=NOW, price=100, quantity=10, side=PositionSide.LONG)
        t.open_position(fill)
        assert not t.is_flat
        assert t.side == PositionSide.LONG
        assert t.quantity == 10

    def test_cannot_double_open(self):
        t = PositionTracker()
        fill1 = Fill(timestamp=NOW, price=100, quantity=10, side=PositionSide.LONG)
        fill2 = Fill(timestamp=NOW + timedelta(hours=1), price=105, quantity=5, side=PositionSide.LONG)
        t.open_position(fill1)
        t.open_position(fill2)
        assert t.quantity == 10  # unchanged

    def test_close_long_pnl(self):
        t = PositionTracker()
        fill_in = Fill(timestamp=NOW, price=100, quantity=10, side=PositionSide.LONG)
        t.open_position(fill_in)
        fill_out = Fill(
            timestamp=NOW + timedelta(days=1),
            price=110,
            quantity=10,
            side=PositionSide.SHORT,
        )
        trade = t.close_position(fill_out)
        assert trade is not None
        assert trade.pnl == pytest.approx(100.0, abs=0.01)
        assert t.is_flat

    def test_close_short_pnl(self):
        t = PositionTracker()
        fill_in = Fill(timestamp=NOW, price=100, quantity=10, side=PositionSide.SHORT)
        t.open_position(fill_in)
        fill_out = Fill(
            timestamp=NOW + timedelta(days=1),
            price=90,
            quantity=10,
            side=PositionSide.LONG,
        )
        trade = t.close_position(fill_out)
        assert trade is not None
        assert trade.pnl == pytest.approx(100.0, abs=0.01)

    def test_unrealized_pnl_long(self):
        t = PositionTracker()
        fill = Fill(timestamp=NOW, price=100, quantity=10, side=PositionSide.LONG)
        t.open_position(fill)
        t.update_unrealized(105)
        assert t.unrealized_pnl == pytest.approx(50.0)

    def test_unrealized_pnl_short(self):
        t = PositionTracker()
        fill = Fill(timestamp=NOW, price=100, quantity=10, side=PositionSide.SHORT)
        t.open_position(fill)
        t.update_unrealized(95)
        assert t.unrealized_pnl == pytest.approx(50.0)

    def test_holding_periods_increment(self):
        t = PositionTracker()
        fill = Fill(timestamp=NOW, price=100, quantity=10, side=PositionSide.LONG)
        t.open_position(fill)
        t.increment_holding()
        t.increment_holding()
        assert t.holding_periods == 2


# ── Cost Model Tests ──


class TestCostModels:
    def test_no_cost(self):
        m = NoCostModel()
        c = m.compute(100, 10, "buy")
        assert c.total == 0.0

    def test_fixed_cost(self):
        m = FixedCostModel(commission_rate=0.001, slippage_bps=5, spread_bps=2)
        c = m.compute(100, 10, "buy")
        assert c.commission == pytest.approx(1.0)
        assert c.slippage == pytest.approx(0.5)
        assert c.spread == pytest.approx(0.2)
        assert c.total == pytest.approx(1.7)

    def test_slippage_model_no_volume(self):
        m = SlippageModel(base_bps=10, commission_rate=0.001)
        c = m.compute(100, 10, "buy", bar_volume=0)
        assert c.total > 0

    def test_slippage_model_with_volume(self):
        m = SlippageModel(base_bps=10, volume_impact_factor=0.5, commission_rate=0.001)
        c_small = m.compute(100, 1, "buy", bar_volume=1000)
        c_large = m.compute(100, 500, "buy", bar_volume=1000)
        assert c_large.slippage > c_small.slippage


# ── Metrics Tests ──


class TestPerformanceMetrics:
    def test_empty_equity(self):
        m = compute_metrics([], [], [])
        assert m.total_return == 0.0

    def test_flat_equity(self):
        eq = [100000.0] * 10
        m = compute_metrics(eq, [], [])
        assert m.total_return == 0.0

    def test_positive_return(self):
        eq = [100000, 105000, 110000]
        m = compute_metrics(eq, [5000, 5000], [1, 1])
        assert m.total_return > 0
        assert m.net_pnl > 0

    def test_negative_return(self):
        eq = [100000, 95000, 90000]
        m = compute_metrics(eq, [-5000, -5000], [1, 1])
        assert m.total_return < 0

    def test_win_rate(self):
        eq = [100000, 102000, 101000, 103000, 102000]
        pnls = [2000, -1000, 2000, -1000]
        m = compute_metrics(eq, pnls, [1, 1, 1, 1])
        assert m.win_rate == pytest.approx(0.5)

    def test_sharpe_ratio(self):
        # Monotonically increasing equity → positive Sharpe
        eq = [100 + i * 0.1 for i in range(50)]
        m = compute_metrics(eq, [0.1] * 49, [1] * 49)
        assert m.sharpe_ratio > 0

    def test_sortino_ratio(self):
        # Mixed returns — some negative, some positive
        eq = [100, 101, 99, 102, 100, 103, 101, 104, 102, 105]
        m = compute_metrics(eq, [], [])
        assert m.sortino_ratio > 0

    def test_max_drawdown(self):
        eq = [100, 110, 90, 100, 80, 100]
        m = compute_metrics(eq, [], [])
        assert m.max_drawdown > 0

    def test_profit_factor(self):
        eq = [100000, 102000, 101000, 103000]
        pnls = [2000, -1000, 2000]
        m = compute_metrics(eq, pnls, [1, 1, 1])
        assert m.profit_factor == pytest.approx(4.0, abs=0.01)

    def test_zero_std_gives_zero_sharpe(self):
        eq = [100.0] * 5
        m = compute_metrics(eq, [], [])
        assert m.sharpe_ratio == 0.0

    def test_costs_deducted(self):
        eq = [100000, 105000]
        m = compute_metrics(eq, [5000], [1], total_costs=500)
        assert m.net_pnl == pytest.approx(4500.0)


# ── Risk Metrics Tests ──


class TestRiskMetrics:
    def test_empty(self):
        r = compute_risk_metrics([])
        assert r.max_drawdown == 0.0

    def test_no_drawdown(self):
        eq = list(range(100, 200))
        r = compute_risk_metrics(eq)
        assert r.max_drawdown == 0.0

    def test_drawdown_detected(self):
        eq = [100, 110, 90, 100]
        r = compute_risk_metrics(eq)
        assert r.max_drawdown > 0
        assert r.max_drawdown == pytest.approx(0.1818, abs=0.01)

    def test_var_95(self):
        import random
        random.seed(42)
        eq = [100.0]
        for _ in range(1000):
            eq.append(eq[-1] * (1 + random.gauss(0, 0.01)))
        r = compute_risk_metrics(eq)
        assert r.value_at_risk_95 < 0

    def test_cvar_worse_than_var(self):
        import random
        random.seed(42)
        eq = [100.0]
        for _ in range(1000):
            eq.append(eq[-1] * (1 + random.gauss(0, 0.01)))
        r = compute_risk_metrics(eq)
        assert r.conditional_var_95 <= r.value_at_risk_95

    def test_ulcer_index(self):
        eq = [100, 110, 90, 100, 80, 100]
        r = compute_risk_metrics(eq)
        assert r.ulcer_index > 0

    def test_volatility_annualized(self):
        import random
        random.seed(42)
        eq = [100.0]
        for _ in range(252):
            eq.append(eq[-1] * (1 + random.gauss(0, 0.01)))
        r = compute_risk_metrics(eq)
        assert r.volatility_annualized > 0


# ── Backtest Engine Tests ──


class TestBacktestEngine:
    def test_flat_strategy_no_trades(self):
        ds = _dataset(_make_bars(50))
        engine = BacktestEngine(strategy=_AlwaysFlatStrategy(), initial_equity=100000)
        result = engine.run(ds)
        assert result.metrics.total_trades == 0
        assert result.initial_equity == 100000

    def test_always_long_opens_position(self):
        ds = _dataset(_make_bars(20))
        engine = BacktestEngine(strategy=_AlwaysLongStrategy(), initial_equity=100000)
        result = engine.run(ds)
        assert result.metrics.total_trades >= 1

    def test_equity_curve_length(self):
        bars = _make_bars(30)
        ds = _dataset(bars)
        engine = BacktestEngine(strategy=_AlwaysFlatStrategy(), initial_equity=100000)
        result = engine.run(ds)
        assert len(result.equity_curve) == len(bars) + 1

    def test_with_transaction_costs(self):
        ds = _dataset(_make_bars(50))
        engine = BacktestEngine(
            strategy=_AlwaysLongStrategy(),
            cost_model=FixedCostModel(commission_rate=0.001),
            initial_equity=100000,
        )
        result = engine.run(ds)
        assert result.total_cost > 0

    def test_no_cost_model(self):
        ds = _dataset(_make_bars(50))
        engine = BacktestEngine(
            strategy=_AlwaysLongStrategy(),
            cost_model=NoCostModel(),
            initial_equity=100000,
        )
        result = engine.run(ds)
        assert result.total_cost == 0

    def test_chronological_validation(self):
        bars = _make_bars(5)
        bars_list = list(bars)
        bars_list[1], bars_list[3] = bars_list[3], bars_list[1]
        ds = Dataset(
            bars=bars_list,
            provenance=Provenance(source="test", symbol="X", frequency="daily", total_bars=5),
            metadata=DatasetMetadata(name="bad"),
            quality=QualityReport(total_bars=5),
        )
        engine = BacktestEngine(strategy=_AlwaysFlatStrategy())
        with pytest.raises(ValueError, match="chronological"):
            engine.run(ds)

    def test_no_future_leakage(self):
        bars = _make_bars(50)
        ds = _dataset(bars)
        strategy = _NoFutureStrategy()
        engine = BacktestEngine(strategy=strategy, initial_equity=100000)
        result = engine.run(ds)
        assert result is not None

    def test_summary_dict(self):
        ds = _dataset(_make_bars(20))
        engine = BacktestEngine(strategy=_AlwaysLongStrategy(), initial_equity=100000)
        result = engine.run(ds)
        summary = result.summary()
        assert "initial_equity" in summary
        assert "final_equity" in summary
        assert "sharpe_ratio" in summary
        assert "max_drawdown" in summary

    def test_zero_equity(self):
        ds = _dataset(_make_bars(10))
        engine = BacktestEngine(strategy=_AlwaysLongStrategy(), initial_equity=0)
        result = engine.run(ds)
        assert result.metrics.total_trades == 0

    def test_single_bar(self):
        ds = _dataset(_make_bars(1))
        engine = BacktestEngine(strategy=_AlwaysFlatStrategy(), initial_equity=100000)
        result = engine.run(ds)
        assert len(result.equity_curve) == 2

    def test_deterministic(self):
        ds = _dataset(_make_bars(30))
        r1 = BacktestEngine(strategy=_AlwaysLongStrategy(), initial_equity=100000).run(ds)
        r2 = BacktestEngine(strategy=_AlwaysLongStrategy(), initial_equity=100000).run(ds)
        assert r1.equity_curve == r2.equity_curve
        assert r1.metrics.total_trades == r2.metrics.total_trades

    def test_position_size_affects_quantity(self):
        ds = _dataset(_make_bars(10))
        r1 = BacktestEngine(
            strategy=_AlwaysLongStrategy(), initial_equity=100000, position_size=0.5
        ).run(ds)
        r2 = BacktestEngine(
            strategy=_AlwaysLongStrategy(), initial_equity=100000, position_size=1.0
        ).run(ds)
        assert r2.metrics.total_costs >= r1.metrics.total_costs


# ── StrategyConfig Tests ──


class TestStrategyConfig:
    def test_config(self):
        cfg = StrategyConfig(name="test", version="2.0", lookback=10)
        assert cfg.name == "test"
        assert cfg.version == "2.0"
        assert cfg.lookback == 10

    def test_default_parameters(self):
        cfg = StrategyConfig(name="test")
        assert cfg.parameters == {}
