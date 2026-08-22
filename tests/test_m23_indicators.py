"""Comprehensive tests for M23 indicators.

Covers: Stochastic, ADX/DMI, CCI, ROC, Williams %R, OBV, VWAP, MFI,
Ichimoku, Pivot Points, Fibonacci.

Includes leakage-protection and determinism test classes.
"""

from __future__ import annotations

import pytest

from aurora.features.indicators import (
    adx_dmi,
    cci,
    fibonacci_retracement,
    ichimoku,
    mfi,
    obv,
    pivot_points,
    roc,
    stochastic,
    vwap,
    williams_r,
)


def _assert_close(a: float, b: float, tol: float = 1e-10) -> None:
    assert a == pytest.approx(b, abs=tol), f"{a} != {b}"


def _lists_equal(a: list, b: list, tol: float = 1e-10) -> None:
    assert len(a) == len(b), f"length mismatch: {len(a)} vs {len(b)}"
    for i, (va, vb) in enumerate(zip(a, b)):
        if va is None and vb is None:
            continue
        if va is None or vb is None:
            raise AssertionError(f"index {i}: {va!r} != {vb!r}")
        _assert_close(va, vb, tol)


def _make_ohlc(n: int = 30, seed: float = 100.0) -> tuple[list[float], list[float], list[float]]:
    highs: list[float] = []
    lows: list[float] = []
    closes: list[float] = []
    for i in range(n):
        base = seed + i * 0.5
        highs.append(base + 1.0)
        lows.append(base - 0.5)
        closes.append(base + 0.3)
    return highs, lows, closes


def _make_vol(n: int = 30) -> list[float]:
    return [1000.0 + i * 10.0 for i in range(n)]


class TestStochastic:
    def test_basic_output_shape(self) -> None:
        h, l, c = _make_ohlc(30)
        result = stochastic(h, l, c)
        assert "k" in result
        assert "d" in result
        assert len(result["k"]) == 30
        assert len(result["d"]) == 30

    def test_range_0_to_100(self) -> None:
        h, l, c = _make_ohlc(50)
        result = stochastic(h, l, c)
        for v in result["k"]:
            if v is not None:
                assert 0.0 <= v <= 100.0, f"%K out of range: {v}"
        for v in result["d"]:
            if v is not None:
                assert 0.0 <= v <= 100.0, f"%D out of range: {v}"

    def test_constant_price_gives_50(self) -> None:
        n = 20
        h = [105.0] * n
        l = [95.0] * n
        c = [100.0] * n
        result = stochastic(h, l, c)
        for v in result["k"]:
            if v is not None:
                assert v == 50.0
        for v in result["d"]:
            if v is not None:
                assert v == 50.0

    def test_insufficient_data_all_none(self) -> None:
        h, l, c = _make_ohlc(5)
        result = stochastic(h, l, c, k_period=14)
        for v in result["k"][:5]:
            assert v is None

    def test_custom_params(self) -> None:
        h, l, c = _make_ohlc(40)
        r1 = stochastic(h, l, c, k_period=5, d_period=3, smooth_k=3)
        r2 = stochastic(h, l, c, k_period=10, d_period=5, smooth_k=5)
        assert r1["k"] != r2["k"]

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="same length"):
            stochastic([1.0, 2.0], [1.0], [1.0, 2.0])

    def test_first_k_period_minus_1_none(self) -> None:
        h, l, c = _make_ohlc(20)
        result = stochastic(h, l, c, k_period=10)
        for i in range(9):
            assert result["k"][i] is None
        # k_raw first valid at index 9, but smoothed by smooth_k=3,
        # so first non-None smoothed K needs 3 valid k_raw values
        for i in range(11):
            assert result["k"][i] is None
        assert result["k"][11] is not None


class TestAdxDmi:
    def test_basic_output_keys(self) -> None:
        h, l, c = _make_ohlc(40)
        result = adx_dmi(h, l, c)
        assert set(result.keys()) == {"plus_di", "minus_di", "adx"}
        assert len(result["plus_di"]) == 40

    def test_short_data_all_none(self) -> None:
        h, l, c = _make_ohlc(3)
        result = adx_dmi(h, l, c)
        for key in result:
            for v in result[key]:
                assert v is None

    def test_deterministic(self) -> None:
        h, l, c = _make_ohlc(50)
        r1 = adx_dmi(h, l, c, period=14)
        r2 = adx_dmi(h, l, c, period=14)
        for key in r1:
            _lists_equal(r1[key], r2[key])

    def test_custom_period(self) -> None:
        h, l, c = _make_ohlc(60)
        r1 = adx_dmi(h, l, c, period=7)
        r2 = adx_dmi(h, l, c, period=20)
        assert r1["adx"] != r2["adx"]

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="same length"):
            adx_dmi([1.0, 2.0], [1.0], [1.0, 2.0])


class TestCCI:
    def test_basic_output_length(self) -> None:
        h, l, c = _make_ohlc(30)
        result = cci(h, l, c, period=20)
        assert len(result) == 30

    def test_constant_price_gives_zero(self) -> None:
        n = 30
        h = [105.0] * n
        l = [95.0] * n
        c = [100.0] * n
        result = cci(h, l, c, period=20)
        for v in result:
            if v is not None:
                assert v == 0.0

    def test_insufficient_data_none(self) -> None:
        h, l, c = _make_ohlc(10)
        result = cci(h, l, c, period=20)
        for v in result[:10]:
            assert v is None

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="same length"):
            cci([1.0], [2.0, 3.0], [1.0])


class TestROC:
    def test_basic_output_length(self) -> None:
        values = [100.0 + i for i in range(20)]
        result = roc(values, period=5)
        assert len(result) == 20

    def test_known_value(self) -> None:
        values = [10.0, 20.0, 30.0, 40.0, 50.0, 60.0]
        result = roc(values, period=1)
        assert result[1] == pytest.approx(100.0)
        assert result[5] == pytest.approx(20.0)

    def test_zero_previous_value_returns_none(self) -> None:
        values = [0.0, 10.0, 20.0]
        result = roc(values, period=1)
        assert result[1] is None

    def test_first_period_none(self) -> None:
        values = [10.0, 20.0, 30.0]
        result = roc(values, period=2)
        assert result[0] is None
        assert result[1] is None
        assert result[2] is not None


class TestWilliamsR:
    def test_basic_output_length(self) -> None:
        h, l, c = _make_ohlc(30)
        result = williams_r(h, l, c, period=14)
        assert len(result) == 30

    def test_range_neg100_to_0(self) -> None:
        h, l, c = _make_ohlc(40)
        result = williams_r(h, l, c, period=14)
        for v in result:
            if v is not None:
                assert -100.0 <= v <= 0.0, f"Williams %R out of range: {v}"

    def test_constant_price_gives_neg50(self) -> None:
        n = 20
        h = [105.0] * n
        l = [95.0] * n
        c = [100.0] * n
        result = williams_r(h, l, c, period=14)
        for v in result:
            if v is not None:
                assert v == -50.0

    def test_insufficient_data_none(self) -> None:
        h, l, c = _make_ohlc(5)
        result = williams_r(h, l, c, period=10)
        for v in result:
            assert v is None

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="same length"):
            williams_r([1.0], [2.0, 3.0], [1.0])


class TestOBV:
    def test_basic_output_length(self) -> None:
        closes = [100.0, 101.0, 99.0, 102.0]
        volumes = [1000.0, 1100.0, 900.0, 1200.0]
        result = obv(closes, volumes)
        assert len(result) == 4

    def test_constant_price_volume_unchanged(self) -> None:
        closes = [100.0, 100.0, 100.0]
        volumes = [1000.0, 2000.0, 3000.0]
        result = obv(closes, volumes)
        assert result == [0.0, 0.0, 0.0]

    def test_known_values(self) -> None:
        closes = [10.0, 12.0, 11.0, 13.0]
        volumes = [100.0, 200.0, 300.0, 400.0]
        result = obv(closes, volumes)
        assert result == [0.0, 200.0, -100.0, 300.0]

    def test_empty(self) -> None:
        result: list[float] = obv([], [])
        assert result == []

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="same length"):
            obv([1.0, 2.0], [1.0])


class TestVWAP:
    def test_basic_output_length(self) -> None:
        h, l, c = _make_ohlc(10)
        v = _make_vol(10)
        result = vwap(h, l, c, v)
        assert len(result) == 10

    def test_first_bar_equals_typical_price(self) -> None:
        h, l, c = _make_ohlc(5)
        v = _make_vol(5)
        result = vwap(h, l, c, v)
        tp0 = (h[0] + l[0] + c[0]) / 3.0
        assert result[0] == pytest.approx(tp0)

    def test_zero_volume_gives_none(self) -> None:
        h = [105.0, 106.0]
        l = [95.0, 96.0]
        c = [100.0, 101.0]
        v = [0.0, 0.0]
        result = vwap(h, l, c, v)
        assert result[0] is None
        assert result[1] is None

    def test_empty(self) -> None:
        result = vwap([], [], [], [])
        assert result == []

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="same length"):
            vwap([1.0], [2.0], [3.0], [4.0, 5.0])

    def test_cumulative_correctness(self) -> None:
        h = [110.0, 120.0]
        l = [90.0, 100.0]
        c = [100.0, 110.0]
        v = [1000.0, 2000.0]
        tp0 = (110 + 90 + 100) / 3.0
        tp1 = (120 + 100 + 110) / 3.0
        expected_1 = (tp0 * 1000 + tp1 * 2000) / 3000.0
        result = vwap(h, l, c, v)
        assert result[0] == pytest.approx(tp0)
        assert result[1] == pytest.approx(expected_1)


class TestMFI:
    def test_basic_output_length(self) -> None:
        h, l, c = _make_ohlc(30)
        v = _make_vol(30)
        result = mfi(h, l, c, v, period=14)
        assert len(result) == 30

    def test_range_0_to_100(self) -> None:
        h, l, c = _make_ohlc(40)
        v = _make_vol(40)
        result = mfi(h, l, c, v, period=14)
        for val in result:
            if val is not None:
                assert 0.0 <= val <= 100.0, f"MFI out of range: {val}"

    def test_all_positive_flow_gives_100(self) -> None:
        n = 20
        h = [100.0 + i for i in range(n)]
        l = [90.0 + i for i in range(n)]
        c = [95.0 + i for i in range(n)]
        v = [1000.0] * n
        result = mfi(h, l, c, v, period=5)
        for val in result:
            if val is not None:
                assert val == 100.0

    def test_insufficient_data_none(self) -> None:
        h, l, c = _make_ohlc(5)
        v = _make_vol(5)
        result = mfi(h, l, c, v, period=14)
        for val in result:
            assert val is None

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="same length"):
            mfi([1.0, 2.0], [1.0], [1.0, 2.0], [1.0, 2.0])


class TestIchimoku:
    def test_basic_output_keys(self) -> None:
        h, l, c = _make_ohlc(60)
        result = ichimoku(h, l, c)
        assert set(result.keys()) == {
            "tenkan_sen", "kijun_sen", "senkou_a", "senkou_b", "chikou",
        }
        for key in result:
            assert len(result[key]) == 60

    def test_tenkan_sen_range(self) -> None:
        h, l, c = _make_ohlc(30)
        result = ichimoku(h, l, c, tenkan_period=9, kijun_period=26, senkou_b_period=52)
        for i, v in enumerate(result["tenkan_sen"]):
            if v is not None:
                start = max(0, i + 1 - 9)
                window_high = max(h[start:i + 1])
                window_low = min(l[start:i + 1])
                assert window_low <= v <= window_high

    def test_kijun_sen_range(self) -> None:
        h, l, c = _make_ohlc(60)
        result = ichimoku(h, l, c, tenkan_period=9, kijun_period=26, senkou_b_period=52)
        for i, v in enumerate(result["kijun_sen"]):
            if v is not None:
                start = max(0, i + 1 - 26)
                window_high = max(h[start:i + 1])
                window_low = min(l[start:i + 1])
                assert window_low <= v <= window_high

    def test_insufficient_data_none(self) -> None:
        h, l, c = _make_ohlc(5)
        result = ichimoku(h, l, c, tenkan_period=9, kijun_period=26, senkou_b_period=52)
        assert result["tenkan_sen"][0] is None
        assert result["kijun_sen"][0] is None
        assert result["senkou_b"][0] is None

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="same length"):
            ichimoku([1.0, 2.0], [1.0], [1.0, 2.0])

    def test_deterministic(self) -> None:
        h, l, c = _make_ohlc(60)
        r1 = ichimoku(h, l, c)
        r2 = ichimoku(h, l, c)
        for key in r1:
            _lists_equal(r1[key], r2[key])

    def test_chikou_receives_close_at_forward_index(self) -> None:
        closes = [10.0, 20.0, 30.0, 40.0, 50.0]
        highs = [cc + 1 for cc in closes]
        lows = [cc - 1 for cc in closes]
        result = ichimoku(highs, lows, closes, tenkan_period=2, kijun_period=2, senkou_b_period=3)
        assert result["chikou"][0] == 30.0
        assert result["chikou"][1] == 40.0
        assert result["chikou"][2] == 50.0



class TestPivotPoints:
    def test_first_bar_none(self) -> None:
        h, l, c = _make_ohlc(5)
        result = pivot_points(h, l, c)
        for key in result:
            assert result[key][0] is None

    def test_known_hand_calculated(self) -> None:
        h = [100.0, 110.0]
        l = [90.0, 90.0]
        c = [95.0, 100.0]
        result = pivot_points(h, l, c)
        # Bar 1 pivot uses bar 0's data: prev_h=100, prev_l=90, prev_c=95
        p = (100.0 + 90.0 + 95.0) / 3.0
        assert result["pivot"][1] == pytest.approx(p)
        assert result["r1"][1] == pytest.approx(2.0 * p - 90.0)
        assert result["r2"][1] == pytest.approx(p + (100.0 - 90.0))
        assert result["r3"][1] == pytest.approx(100.0 + 2.0 * (p - 90.0))
        assert result["s1"][1] == pytest.approx(2.0 * p - 100.0)
        assert result["s2"][1] == pytest.approx(p - (100.0 - 90.0))
        assert result["s3"][1] == pytest.approx(90.0 - 2.0 * (100.0 - p))

    def test_length_mismatch_raises(self) -> None:
        with pytest.raises(ValueError, match="same length"):
            pivot_points([1.0, 2.0], [1.0], [1.0, 2.0])

    def test_all_bars_have_values_except_first(self) -> None:
        h, l, c = _make_ohlc(10)
        result = pivot_points(h, l, c)
        for key in result:
            assert result[key][0] is None
            for i in range(1, 10):
                assert result[key][i] is not None


class TestFibonacci:
    def test_basic_levels(self) -> None:
        result = fibonacci_retracement(200.0, 100.0)
        assert result[0.0] == pytest.approx(200.0)
        assert result[1.0] == pytest.approx(100.0)
        assert result[0.5] == pytest.approx(150.0)

    def test_reversed_high_low_swapped(self) -> None:
        a = fibonacci_retracement(200.0, 100.0)
        b = fibonacci_retracement(100.0, 200.0)
        assert a == b

    def test_custom_levels(self) -> None:
        result = fibonacci_retracement(100.0, 0.0, levels=[0.0, 0.382, 1.0])
        assert len(result) == 3
        assert result[0.0] == pytest.approx(100.0)
        assert result[0.382] == pytest.approx(61.8)
        assert result[1.0] == pytest.approx(0.0)

    def test_single_level(self) -> None:
        result = fibonacci_retracement(150.0, 50.0, levels=[0.5])
        assert len(result) == 1
        assert result[0.5] == pytest.approx(100.0)



class TestLeakageProtection:
    """Changing future bars must not affect indicator values at earlier bars."""

    def _make_series(self, n: int = 20) -> tuple[list[float], list[float], list[float], list[float]]:
        highs = [100.0 + i * 0.7 for i in range(n)]
        lows = [98.0 + i * 0.7 for i in range(n)]
        closes = [99.0 + i * 0.7 for i in range(n)]
        volumes = [1000.0 + i * 50.0 for i in range(n)]
        return highs, lows, closes, volumes

    def _mod_last3(self, series: list[float]) -> list[float]:
        return series[:17] + [200.0, 201.0, 202.0]

    def test_stochastic_leakage(self) -> None:
        h, l, c, _ = self._make_series(20)
        r_full = stochastic(h, l, c, k_period=5, d_period=3, smooth_k=3)
        h_mod = self._mod_last3(h)
        l_mod = self._mod_last3(l)
        c_mod = self._mod_last3(c)
        r_cut = stochastic(h_mod, l_mod, c_mod, k_period=5, d_period=3, smooth_k=3)
        _lists_equal(r_full["k"][:17], r_cut["k"][:17])
        _lists_equal(r_full["d"][:17], r_cut["d"][:17])

    def test_adx_dmi_leakage(self) -> None:
        h, l, c, _ = self._make_series(20)
        r_full = adx_dmi(h, l, c, period=7)
        h_mod = self._mod_last3(h)
        l_mod = self._mod_last3(l)
        c_mod = self._mod_last3(c)
        r_cut = adx_dmi(h_mod, l_mod, c_mod, period=7)
        for key in ("plus_di", "minus_di", "adx"):
            _lists_equal(r_full[key][:17], r_cut[key][:17])

    def test_cci_leakage(self) -> None:
        h, l, c, _ = self._make_series(20)
        r_full = cci(h, l, c, period=10)
        h_mod = self._mod_last3(h)
        l_mod = self._mod_last3(l)
        c_mod = self._mod_last3(c)
        r_cut = cci(h_mod, l_mod, c_mod, period=10)
        _lists_equal(r_full[:17], r_cut[:17])

    def test_roc_leakage(self) -> None:
        _, _, c, _ = self._make_series(20)
        r_full = roc(c, period=5)
        c_mod = self._mod_last3(c)
        r_cut = roc(c_mod, period=5)
        _lists_equal(r_full[:17], r_cut[:17])

    def test_williams_r_leakage(self) -> None:
        h, l, c, _ = self._make_series(20)
        r_full = williams_r(h, l, c, period=10)
        h_mod = self._mod_last3(h)
        l_mod = self._mod_last3(l)
        c_mod = self._mod_last3(c)
        r_cut = williams_r(h_mod, l_mod, c_mod, period=10)
        _lists_equal(r_full[:17], r_cut[:17])

    def test_obv_leakage(self) -> None:
        _, _, c, v = self._make_series(20)
        r_full = obv(c, v)
        c_mod = self._mod_last3(c)
        v_mod = self._mod_last3(v)
        r_cut = obv(c_mod, v_mod)
        _lists_equal(r_full[:17], r_cut[:17])

    def test_vwap_leakage(self) -> None:
        h, l, c, v = self._make_series(20)
        r_full = vwap(h, l, c, v)
        h_mod = self._mod_last3(h)
        l_mod = self._mod_last3(l)
        c_mod = self._mod_last3(c)
        v_mod = self._mod_last3(v)
        r_cut = vwap(h_mod, l_mod, c_mod, v_mod)
        _lists_equal(r_full[:17], r_cut[:17])

    def test_mfi_leakage(self) -> None:
        h, l, c, v = self._make_series(20)
        r_full = mfi(h, l, c, v, period=10)
        h_mod = self._mod_last3(h)
        l_mod = self._mod_last3(l)
        c_mod = self._mod_last3(c)
        v_mod = self._mod_last3(v)
        r_cut = mfi(h_mod, l_mod, c_mod, v_mod, period=10)
        _lists_equal(r_full[:17], r_cut[:17])

    def test_ichimoku_leakage(self) -> None:
        h, l, c, _ = self._make_series(20)
        r_full = ichimoku(h, l, c, tenkan_period=5, kijun_period=7, senkou_b_period=10)
        h_mod = self._mod_last3(h)
        l_mod = self._mod_last3(l)
        c_mod = self._mod_last3(c)
        r_cut = ichimoku(h_mod, l_mod, c_mod, tenkan_period=5, kijun_period=7, senkou_b_period=10)
        for key in ("tenkan_sen", "kijun_sen", "senkou_a", "senkou_b"):
            _lists_equal(r_full[key][:17], r_cut[key][:17])

    def test_pivot_points_leakage(self) -> None:
        h, l, c, _ = self._make_series(20)
        r_full = pivot_points(h, l, c)
        h_mod = self._mod_last3(h)
        l_mod = self._mod_last3(l)
        c_mod = self._mod_last3(c)
        r_cut = pivot_points(h_mod, l_mod, c_mod)
        for key in r_full:
            _lists_equal(r_full[key][:17], r_cut[key][:17])



class TestDeterminism:
    """Running each indicator twice on same data must produce identical results."""

    def test_stochastic_deterministic(self) -> None:
        h, l, c = _make_ohlc(40)
        r1 = stochastic(h, l, c, k_period=7, d_period=3, smooth_k=3)
        r2 = stochastic(h, l, c, k_period=7, d_period=3, smooth_k=3)
        _lists_equal(r1["k"], r2["k"])
        _lists_equal(r1["d"], r2["d"])

    def test_adx_dmi_deterministic(self) -> None:
        h, l, c = _make_ohlc(40)
        r1 = adx_dmi(h, l, c, period=10)
        r2 = adx_dmi(h, l, c, period=10)
        for key in r1:
            _lists_equal(r1[key], r2[key])

    def test_cci_deterministic(self) -> None:
        h, l, c = _make_ohlc(40)
        r1 = cci(h, l, c, period=15)
        r2 = cci(h, l, c, period=15)
        _lists_equal(r1, r2)

    def test_roc_deterministic(self) -> None:
        _, _, c = _make_ohlc(40)
        r1 = roc(c, period=5)
        r2 = roc(c, period=5)
        _lists_equal(r1, r2)

    def test_williams_r_deterministic(self) -> None:
        h, l, c = _make_ohlc(40)
        r1 = williams_r(h, l, c, period=14)
        r2 = williams_r(h, l, c, period=14)
        _lists_equal(r1, r2)

    def test_obv_deterministic(self) -> None:
        _, _, c = _make_ohlc(40)
        v = _make_vol(40)
        r1 = obv(c, v)
        r2 = obv(c, v)
        _lists_equal(r1, r2)

    def test_vwap_deterministic(self) -> None:
        h, l, c = _make_ohlc(40)
        v = _make_vol(40)
        r1 = vwap(h, l, c, v)
        r2 = vwap(h, l, c, v)
        _lists_equal(r1, r2)

    def test_mfi_deterministic(self) -> None:
        h, l, c = _make_ohlc(40)
        v = _make_vol(40)
        r1 = mfi(h, l, c, v, period=10)
        r2 = mfi(h, l, c, v, period=10)
        _lists_equal(r1, r2)

    def test_ichimoku_deterministic(self) -> None:
        h, l, c = _make_ohlc(60)
        r1 = ichimoku(h, l, c)
        r2 = ichimoku(h, l, c)
        for key in r1:
            _lists_equal(r1[key], r2[key])

    def test_pivot_points_deterministic(self) -> None:
        h, l, c = _make_ohlc(40)
        r1 = pivot_points(h, l, c)
        r2 = pivot_points(h, l, c)
        for key in r1:
            _lists_equal(r1[key], r2[key])

    def test_fibonacci_deterministic(self) -> None:
        r1 = fibonacci_retracement(200.0, 100.0)
        r2 = fibonacci_retracement(200.0, 100.0)
        assert r1 == r2

    def test_fibonacci_deterministic_custom(self) -> None:
        r1 = fibonacci_retracement(500.0, 300.0, levels=[0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0])
        r2 = fibonacci_retracement(500.0, 300.0, levels=[0.0, 0.236, 0.382, 0.5, 0.618, 0.786, 1.0])
        assert r1 == r2
