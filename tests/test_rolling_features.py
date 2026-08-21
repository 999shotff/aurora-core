import pytest

from aurora.features.rolling import (
    ema,
    momentum,
    returns,
    rolling_max,
    rolling_mean,
    rolling_min,
    rolling_std,
    sma,
    volume_ratio,
)


def test_rolling_mean_basic():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    result = rolling_mean(values, 3)
    assert result[0] is None
    assert result[1] is None
    assert result[2] == pytest.approx(2.0)
    assert result[3] == pytest.approx(3.0)
    assert result[4] == pytest.approx(4.0)


def test_rolling_mean_window_1():
    values = [10.0, 20.0, 30.0]
    result = rolling_mean(values, 1)
    assert result == [10.0, 20.0, 30.0]


def test_rolling_std_basic():
    values = [2.0, 4.0, 4.0, 4.0, 5.0, 5.0, 7.0, 9.0]
    result = rolling_std(values, 3)
    assert result[0] is None
    assert result[1] is None
    assert result[2] == pytest.approx(0.94280904, abs=1e-6)
    assert result[3] == pytest.approx(0.0)
    assert result[4] == pytest.approx(0.47140452, abs=1e-6)


def test_rolling_max():
    values = [1.0, 3.0, 2.0, 5.0, 4.0]
    result = rolling_max(values, 3)
    assert result[0] is None
    assert result[1] is None
    assert result[2] == 3.0
    assert result[3] == 5.0
    assert result[4] == 5.0


def test_rolling_min():
    values = [5.0, 3.0, 4.0, 1.0, 2.0]
    result = rolling_min(values, 3)
    assert result[0] is None
    assert result[1] is None
    assert result[2] == 3.0
    assert result[3] == 1.0
    assert result[4] == 1.0


def test_ema_basic():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    result = ema(values, 3)
    assert result[0] is None
    assert result[1] is None
    assert result[2] == pytest.approx(2.0)
    assert result[3] == pytest.approx(3.0)
    assert result[4] == pytest.approx(4.0)


def test_ema_converges_to_constant():
    values = [10.0] * 20
    result = ema(values, 5)
    assert result[4] == pytest.approx(10.0)
    assert result[-1] == pytest.approx(10.0)


def test_sma_equals_rolling_mean():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    assert sma(values, 3) == rolling_mean(values, 3)


def test_momentum_basic():
    values = [10.0, 12.0, 11.0, 13.0, 15.0]
    result = momentum(values, 2)
    assert result[0] is None
    assert result[1] is None
    assert result[2] == pytest.approx(1.0)
    assert result[3] == pytest.approx(1.0)
    assert result[4] == pytest.approx(4.0)


def test_momentum_period_1():
    values = [10.0, 12.0, 11.0]
    result = momentum(values, 1)
    assert result == [None, 2.0, -1.0]


def test_returns_basic():
    prices = [100.0, 105.0, 102.0]
    result = returns(prices)
    assert result[0] == pytest.approx(0.05)
    assert result[1] == pytest.approx(-0.0285714, abs=1e-5)


def test_returns_empty():
    assert returns([]) == []
    assert returns([100.0]) == []


def test_volume_ratio_basic():
    volumes = [100.0, 100.0, 100.0, 200.0, 100.0]
    result = volume_ratio(volumes, 3)
    assert result[0] is None
    assert result[1] is None
    assert result[2] == pytest.approx(1.0)
    assert result[3] == pytest.approx(1.5)
    assert result[4] == pytest.approx(0.75)


def test_volume_ratio_zero_average():
    volumes = [0.0, 0.0, 5.0]
    result = volume_ratio(volumes, 3)
    assert result[2] == pytest.approx(3.0)


def test_rolling_mean_invalid_window():
    with pytest.raises(ValueError, match="window must be >= 1"):
        rolling_mean([1.0], 0)


def test_rolling_mean_empty():
    assert rolling_mean([], 3) == []


def test_warmup_behavior():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    result = rolling_mean(values, 3)
    warmup = [v for v in result if v is None]
    assert len(warmup) == 2


def test_no_lookahead():
    values = [1.0, 2.0, 3.0, 4.0, 5.0]
    result = rolling_mean(values, 3)
    for i in range(2, len(values)):
        expected = sum(values[i - 2 : i + 1]) / 3
        assert result[i] == pytest.approx(expected)
