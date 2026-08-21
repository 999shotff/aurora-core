from datetime import datetime, timezone
from pathlib import Path

import pytest

from aurora.evaluation.pipeline import EvaluationPipeline
from aurora.models.stub import StubAdapter
from aurora.schemas.market_state import MarketState


def _make_scenarios_and_outcomes():
    scenarios = []
    outcomes = []
    for i, (asset, direction) in enumerate(
        [
            ("BTCUSD", "up"),
            ("ETHUSD", "down"),
            ("BTCUSD", "up"),
            ("SOLUSD", "down"),
            ("ETHUSD", "up"),
        ]
    ):
        state = MarketState(
            asset=asset,
            timeframe="15m",
            timestamp=datetime(2025, 1, 1, 12, i, tzinfo=timezone.utc),
            data_quality="historical",
            price=100_000.0 + i * 100,
        )
        scenarios.append(state)
        outcomes.append(direction)
    return scenarios, outcomes


def test_pipeline_basic():
    scenarios, outcomes = _make_scenarios_and_outcomes()
    pipeline = EvaluationPipeline(experiment_id="test_001")
    model = StubAdapter()
    result = pipeline.evaluate_model(model, scenarios, outcomes, data_split="test")

    assert result.experiment_id == "test_001"
    assert result.model_id == "stub_v1"
    assert len(result.records) == 5
    assert result.summary["count"] == 5
    assert "mean_brier_score" in result.summary
    assert "accuracy" in result.summary
    assert "abstention_rate" in result.summary


def test_pipeline_save_result(tmp_path: Path):
    scenarios, outcomes = _make_scenarios_and_outcomes()
    pipeline = EvaluationPipeline(experiment_id="test_002")
    model = StubAdapter()
    result = pipeline.evaluate_model(model, scenarios, outcomes, data_split="validation")

    out_path = tmp_path / "results" / "test_002.json"
    pipeline.save_result(result, out_path)
    assert out_path.exists()

    import json
    data = json.loads(out_path.read_text())
    assert data["experiment_id"] == "test_002"
    assert data["record_count"] == 5


def test_pipeline_length_mismatch():
    scenarios = [MarketState(
        asset="BTCUSD",
        timeframe="15m",
        timestamp=datetime.now(timezone.utc),
        data_quality="historical",
        price=100_000.0,
    )]
    outcomes = ["up", "down"]
    pipeline = EvaluationPipeline(experiment_id="test_err")
    model = StubAdapter()
    with pytest.raises(ValueError, match="length mismatch"):
        pipeline.evaluate_model(model, scenarios, outcomes, data_split="test")


def test_pipeline_requires_data_split():
    scenarios, outcomes = _make_scenarios_and_outcomes()
    pipeline = EvaluationPipeline(experiment_id="test_no_split")
    model = StubAdapter()
    with pytest.raises(TypeError):
        pipeline.evaluate_model(model, scenarios, outcomes)
