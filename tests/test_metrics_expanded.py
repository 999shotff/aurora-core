from aurora.evaluation import (
    abstention_quality,
    brier_score,
    calibration_error,
    directional_accuracy,
    mean_brier_score,
    outcome_distribution,
)


def test_brier_score_edge_cases():
    assert brier_score(1.0, True) == 0.0
    assert brier_score(0.0, True) == 1.0
    assert brier_score(0.5, True) == 0.25
    assert brier_score(0.5, False) == 0.25


def test_mean_brier_score():
    records = [(1.0, True), (0.0, False)]
    assert mean_brier_score(records) == 0.0

    records2 = [(0.8, True), (0.2, False)]
    score = mean_brier_score(records2)
    assert abs(score - 0.04) < 1e-10


def test_mean_brier_score_empty():
    assert mean_brier_score([]) == 0.0


def test_directional_accuracy():
    assert directional_accuracy("up", "up") is True
    assert directional_accuracy("up", "down") is False
    assert directional_accuracy("unknown", "up") is None
    assert directional_accuracy("up", "unknown") is None
    assert directional_accuracy("abstain", "down") is None


def test_calibration_error_empty():
    assert calibration_error([]) == 0.0


def test_calibration_error_perfect():
    predictions = [(0.5, True), (0.5, False)]
    error = calibration_error(predictions)
    assert isinstance(error, float)


def test_calibration_error_perfect_calibration():
    predictions = [(0.8, True)] * 8 + [(0.8, False)] * 2
    error = calibration_error(predictions)
    assert abs(error - 0.05) < 1e-10


def test_calibration_error_worst_case():
    predictions = [(0.9, False)] * 10
    error = calibration_error(predictions)
    assert error > 0.9


def test_calibration_error_known_value():
    predictions = [(0.7, True)] * 7 + [(0.7, False)] * 3
    error = calibration_error(predictions)
    expected_abs = abs(0.75 - 0.7)
    assert abs(error - expected_abs) < 1e-10


def test_calibration_error_multiple_bins():
    bin0 = [(0.1, True)] * 1 + [(0.1, False)] * 9
    bin9 = [(0.9, True)] * 9 + [(0.9, False)] * 1
    predictions = bin0 + bin9
    error = calibration_error(predictions)
    expected = (
        abs(0.05 - 0.1) * 10 + abs(0.95 - 0.9) * 10
    ) / 20
    assert abs(error - expected) < 1e-10


def test_calibration_error_symmetric():
    predictions_up = [(0.8, True)] * 8 + [(0.8, False)] * 2
    predictions_down = [(0.2, True)] * 2 + [(0.2, False)] * 8
    error_up = calibration_error(predictions_up)
    error_down = calibration_error(predictions_down)
    assert abs(error_up - error_down) < 1e-10


def test_abstention_quality():
    abstained = [True, False, False, True]
    correct = [None, True, False, None]
    result = abstention_quality(abstained, correct)
    assert result["abstention_rate"] == 0.5
    assert abs(result["non_abstain_accuracy"] - 0.5) < 1e-10


def test_abstention_quality_empty():
    result = abstention_quality([], [])
    assert result["abstention_rate"] == 0.0
    assert result["non_abstain_accuracy"] == 0.0


def test_outcome_distribution():
    outcomes = ["up", "down", "up", "up", "abstain"]
    dist = outcome_distribution(outcomes)
    assert dist["up"] == 3
    assert dist["down"] == 1
    assert dist["abstain"] == 1
