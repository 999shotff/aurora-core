from aurora.evaluation import brier_score


def test_brier_score():
    assert brier_score(1.0, True) == 0.0
    assert brier_score(0.0, True) == 1.0
