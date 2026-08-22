
"""M23.1 Indicator Engine - validation, parity, and leakage tests."""

from __future__ import annotations

import time

import pytest

from aurora.features.indicators import (
    adx_dmi,
    atr,
    bollinger_bands,
    cci,
    fibonacci_retracement,
    ichimoku,
    mfi,
    obv,
    pivot_points,
    roc,
    rsi,
    sma_indicator,
    stochastic,
    vwap,
    williams_r,
)
from aurora.features.rolling import ema


def _lists_equal(a, b, tol=1e-10):
    assert len(a) == len(b)
    for i, (va, vb) in enumerate(zip(a, b)):
        if va is None and vb is None:
            continue
        if va is None or vb is None:
            raise AssertionError(f'index {i}: {va!r} != {vb!r}')
        assert va == pytest.approx(vb, abs=tol), f'{va} != {vb}'


def _make_ohlc(n=30, seed=100.0):
    highs = [seed + i * 0.5 + 1.0 for i in range(n)]
    lows = [seed + i * 0.5 - 0.5 for i in range(n)]
    closes = [seed + i * 0.5 + 0.3 for i in range(n)]
    return highs, lows, closes


def _make_vol(n=30):
    return [1000.0 + i * 10.0 for i in range(n)]


def _mod_last3(series):
    return series[:-3] + [200.0, 201.0, 202.0]


class TestSMAEdgeCases:
    def test_empty(self):
        assert sma_indicator([], 5) == []
    def test_single_value(self):
        assert sma_indicator([10.0], 3) == [None]
    def test_exact_period(self):
        r = sma_indicator([1.0, 2.0, 3.0], 3)
        assert r[0] is None and r[1] is None
        assert r[2] == pytest.approx(2.0)
    def test_constant_price(self):
        for v in sma_indicator([5.0] * 10, 5):
            if v is not None:
                assert v == pytest.approx(5.0)


class TestEMAEdgeCases:
    def test_empty(self):
        assert ema([], 5) == []
    def test_shorter_than_period(self):
        assert all(v is None for v in ema([1.0, 2.0], 5))
    def test_exact_period(self):
        r = ema([1.0, 2.0, 3.0], 3)
        assert r[0] is None and r[1] is None
        assert r[2] == pytest.approx(2.0)


class TestRSIEdgeCases:
    def test_empty(self):
        assert rsi([], 14) == []
    def test_single_value(self):
        assert rsi([100.0], 14) == [None]
    def test_two_insufficient(self):
        assert all(v is None for v in rsi([100.0, 101.0], 14))


class TestATREdgeCases:
    def test_empty(self):
        assert atr([], [], [], window=14) == []
    def test_single_bar(self):
        assert atr([110.0], [95.0], [105.0], window=14) == [None]
    def test_length_mismatch(self):
        with pytest.raises(ValueError, match='same length'):
            atr([1.0, 2.0], [1.0], [1.0, 2.0])


class TestBollingerEdgeCases:
    def test_empty(self):
        r = bollinger_bands([], period=20)
        assert r['upper'] == [] and r['middle'] == [] and r['lower'] == []
    def test_fewer_than_period(self):
        r = bollinger_bands([1.0, 2.0, 3.0], period=20)
        assert all(v is None for v in r['upper'])
    def test_constant_price_zero_std(self):
        r = bollinger_bands([100.0] * 30, period=20)
        for i in range(20, 30):
            assert r['upper'][i] == pytest.approx(100.0)
            assert r['lower'][i] == pytest.approx(100.0)


class TestStochasticEdgeCases:
    def test_empty(self):
        r = stochastic([], [], [])
        assert r['k'] == [] and r['d'] == []
    def test_length_mismatch(self):
        with pytest.raises(ValueError, match='same length'):
            stochastic([1.0, 2.0], [1.0], [1.0, 2.0])


class TestAdxDmiEdgeCases:
    def test_empty(self):
        r = adx_dmi([], [], [])
        assert r['plus_di'] == [] and r['adx'] == []
    def test_single_bar(self):
        r = adx_dmi([110.0], [95.0], [105.0])
        assert r['plus_di'] == [None] and r['adx'] == [None]
    def test_length_mismatch(self):
        with pytest.raises(ValueError, match='same length'):
            adx_dmi([1.0, 2.0], [1.0], [1.0, 2.0])


class TestCCIEdgeCases:
    def test_empty(self):
        assert cci([], [], []) == []
    def test_length_mismatch(self):
        with pytest.raises(ValueError, match='same length'):
            cci([1.0], [2.0, 3.0], [1.0])


class TestROCEdgeCases:
    def test_empty(self):
        assert roc([], period=12) == []
    def test_insufficient(self):
        assert all(v is None for v in roc([100.0, 101.0], period=5))


class TestWilliamsREdgeCases:
    def test_empty(self):
        assert williams_r([], [], []) == []
    def test_length_mismatch(self):
        with pytest.raises(ValueError, match='same length'):
            williams_r([1.0], [2.0, 3.0], [1.0])


class TestOBVEdgeCases:
    def test_empty(self):
        assert obv([], []) == []
    def test_single_bar(self):
        assert obv([100.0], [1000.0]) == [0.0]
    def test_length_mismatch(self):
        with pytest.raises(ValueError, match='same length'):
            obv([1.0, 2.0], [1.0])


class TestVWAPEdgeCases:
    def test_empty(self):
        assert vwap([], [], [], []) == []
    def test_zero_volume(self):
        assert vwap([110.0], [95.0], [105.0], [0.0]) == [None]


class TestMFIEdgeCases:
    def test_empty(self):
        assert mfi([], [], [], [], period=14) == []
    def test_insufficient(self):
        h, l, c = _make_ohlc(5)
        assert all(v is None for v in mfi(h, l, c, _make_vol(5), period=14))
    def test_length_mismatch(self):
        with pytest.raises(ValueError, match='same length'):
            mfi([1.0, 2.0], [1.0], [1.0, 2.0], [1.0, 2.0])


class TestIchimokuEdgeCases:
    def test_empty(self):
        r = ichimoku([], [], [])
        for key in r:
            assert r[key] == []
    def test_length_mismatch(self):
        with pytest.raises(ValueError, match='same length'):
            ichimoku([1.0, 2.0], [1.0], [1.0, 2.0])


class TestPivotPointsEdgeCases:
    def test_empty(self):
        r = pivot_points([], [], [])
        for key in r:
            assert all(v is None for v in r[key])
    def test_length_mismatch(self):
        with pytest.raises(ValueError, match='same length'):
            pivot_points([1.0, 2.0], [1.0], [1.0, 2.0])


class TestFibonacciEdgeCases:
    def test_reversed_high_low(self):
        assert fibonacci_retracement(200.0, 100.0) == fibonacci_retracement(100.0, 200.0)
    def test_zero_range(self):
        for price in fibonacci_retracement(100.0, 100.0).values():
            assert price == pytest.approx(100.0)


# ============================================================
# Leakage tests for original indicators (SMA, EMA, RSI, ATR, Bollinger)
# ============================================================


class TestSMALeakage:
    def test_sma_no_future_leakage(self):
        closes = [99.0 + i * 0.7 for i in range(30)]
        r_full = sma_indicator(closes, 10)
        c_mod = _mod_last3(closes)
        r_cut = sma_indicator(c_mod, 10)
        _lists_equal(r_full[:27], r_cut[:27])


class TestEMALeakage:
    def test_ema_no_future_leakage(self):
        closes = [99.0 + i * 0.7 for i in range(30)]
        r_full = ema(closes, 10)
        c_mod = _mod_last3(closes)
        r_cut = ema(c_mod, 10)
        _lists_equal(r_full[:27], r_cut[:27])


class TestRSILeakageExtended:
    def test_rsi_no_future_leakage(self):
        closes = [99.0 + i * 0.7 for i in range(30)]
        r_full = rsi(closes, 10)
        c_mod = _mod_last3(closes)
        r_cut = rsi(c_mod, 10)
        _lists_equal(r_full[:27], r_cut[:27])


class TestATRLeakageExtended:
    def test_atr_no_future_leakage(self):
        h, l, c = _make_ohlc(30)
        r_full = atr(h, l, c, window=10)
        r_cut = atr(_mod_last3(h), _mod_last3(l), _mod_last3(c), window=10)
        _lists_equal(r_full[:27], r_cut[:27])


class TestBollingerLeakage:
    def test_bollinger_no_future_leakage(self):
        closes = [99.0 + i * 0.7 for i in range(30)]
        r_full = bollinger_bands(closes, period=10)
        c_mod = _mod_last3(closes)
        r_cut = bollinger_bands(c_mod, period=10)
        _lists_equal(r_full['upper'][:27], r_cut['upper'][:27])
        _lists_equal(r_full['middle'][:27], r_cut['middle'][:27])
        _lists_equal(r_full['lower'][:27], r_cut['lower'][:27])


# ============================================================
# Parameter variation tests
# ============================================================


class TestParameterVariation:
    def test_sma_different_periods(self):
        closes = [99.0 + i * 0.7 for i in range(50)]
        r5 = sma_indicator(closes, 5)
        r20 = sma_indicator(closes, 20)
        assert r5 != r20
    def test_rsi_different_periods(self):
        closes = [99.0 + i * 0.7 for i in range(50)]
        r7 = rsi(closes, 7)
        r14 = rsi(closes, 14)
        assert r7 != r14
    def test_bollinger_different_periods(self):
        closes = [99.0 + i * 0.7 for i in range(50)]
        r10 = bollinger_bands(closes, period=10, num_std=2)
        r20 = bollinger_bands(closes, period=20, num_std=2)
        assert r10['upper'] != r20['upper']
    def test_stochastic_different_params(self):
        h, l, c = _make_ohlc(40)
        r1 = stochastic(h, l, c, k_period=5, d_period=3, smooth_k=3)
        r2 = stochastic(h, l, c, k_period=14, d_period=5, smooth_k=5)
        assert r1['k'] != r2['k']


# ============================================================
# Performance benchmarks
# ============================================================


class TestPerformance:
    def _bench(self, func, *args, n_runs=10):
        start = time.perf_counter()
        for _ in range(n_runs):
            func(*args)
        elapsed = time.perf_counter() - start
        return elapsed / n_runs

    def test_sma_100_candles(self):
        closes = [99.0 + i * 0.7 for i in range(100)]
        elapsed = self._bench(sma_indicator, closes, 20)
        assert elapsed < 0.1

    def test_rsi_100_candles(self):
        closes = [99.0 + i * 0.7 for i in range(100)]
        elapsed = self._bench(rsi, closes, 14)
        assert elapsed < 0.1

    def test_sma_1000_candles(self):
        closes = [99.0 + i * 0.7 for i in range(1000)]
        elapsed = self._bench(sma_indicator, closes, 20)
        assert elapsed < 0.5

    def test_rsi_1000_candles(self):
        closes = [99.0 + i * 0.7 for i in range(1000)]
        elapsed = self._bench(rsi, closes, 14)
        assert elapsed < 0.5

    def test_bollinger_5000_candles(self):
        closes = [99.0 + i * 0.7 for i in range(5000)]
        elapsed = self._bench(bollinger_bands, closes, 20, 2.0)
        assert elapsed < 2.0

    def test_adx_1000_candles(self):
        h, l, c = _make_ohlc(1000)
        elapsed = self._bench(adx_dmi, h, l, c, 14)
        assert elapsed < 1.0

    def test_stochastic_1000_candles(self):
        h, l, c = _make_ohlc(1000)
        elapsed = self._bench(stochastic, h, l, c, 14, 3, 3)
        assert elapsed < 1.0


# ============================================================
# Determinism tests for original indicators
# ============================================================


class TestDeterminismExtended:
    def test_sma_deterministic(self):
        closes = [99.0 + i * 0.7 for i in range(50)]
        _lists_equal(sma_indicator(closes, 10), sma_indicator(closes, 10))
    def test_ema_deterministic(self):
        closes = [99.0 + i * 0.7 for i in range(50)]
        _lists_equal(ema(closes, 10), ema(closes, 10))
    def test_rsi_deterministic(self):
        closes = [99.0 + i * 0.7 for i in range(50)]
        _lists_equal(rsi(closes, 14), rsi(closes, 14))
    def test_atr_deterministic(self):
        h, l, c = _make_ohlc(50)
        _lists_equal(atr(h, l, c, 14), atr(h, l, c, 14))
    def test_bollinger_deterministic(self):
        closes = [99.0 + i * 0.7 for i in range(50)]
        r1 = bollinger_bands(closes, 20, 2.0)
        r2 = bollinger_bands(closes, 20, 2.0)
        _lists_equal(r1['upper'], r2['upper'])
        _lists_equal(r1['lower'], r2['lower'])
